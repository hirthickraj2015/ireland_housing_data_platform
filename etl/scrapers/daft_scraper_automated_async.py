"""
Fully Automated Daft.ie Scraper using Async Playwright
Works in Jupyter notebooks and command line
Handles Cloudflare challenges automatically - NO manual cookie extraction needed!
"""
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import re
from bs4 import BeautifulSoup

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from etl.config import Config
from etl.utils.logger import get_logger
from etl.utils.database import db

logger = get_logger(__name__)


class DaftScraperAutomatedAsync:
    """
    Fully automated Daft.ie scraper using Async Playwright
    Works in Jupyter notebooks (handles asyncio event loop)
    """

    def __init__(self, headless: bool = True):
        """
        Initialize automated scraper

        Args:
            headless: Run browser in headless mode (True for production, False for debugging)
        """
        self.base_url = Config.DAFT_BASE_URL
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        logger.info(f"Initialized async Daft scraper (headless={headless})")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_browser()

    async def start_browser(self):
        """Start Playwright browser"""
        logger.info("Starting browser...")

        self.playwright = await async_playwright().start()

        # Launch browser with anti-detection settings
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='Europe/Dublin',
        )

        # Add extra HTTP headers
        await self.context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        })

        # Create page
        self.page = await self.context.new_page()

        logger.info("Browser started successfully")

    async def close_browser(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        logger.info("Browser closed")

    async def wait_for_cloudflare(self, timeout: int = 30000):
        """
        Wait for Cloudflare challenge to complete

        Args:
            timeout: Maximum time to wait in milliseconds
        """
        logger.info("Waiting for Cloudflare challenge...")

        try:
            # Wait for challenge to complete by checking for content
            await self.page.wait_for_selector(
                'div[data-testid="search-result"], a[href*="/for-rent/"]',
                timeout=timeout,
                state='visible'
            )
            logger.info("Cloudflare challenge passed!")
            return True

        except PlaywrightTimeoutError:
            logger.warning("Cloudflare challenge timeout - continuing anyway")
            return False

    async def scrape_listings(self, max_pages: int = 10) -> List[Dict]:
        """
        Scrape rental listings from Daft.ie

        Args:
            max_pages: Maximum number of pages to scrape

        Returns:
            List of property dictionaries
        """
        logger.info(f"Starting automated scrape for {max_pages} pages")

        if not self.page:
            await self.start_browser()

        all_listings = []

        try:
            for page_num in range(1, max_pages + 1):
                offset = (page_num - 1) * 20
                url = f"{self.base_url}/property-for-rent/ireland?pageSize=20&from={offset}"

                logger.info(f"Scraping page {page_num}/{max_pages}: {url}")

                # Navigate to page
                try:
                    await self.page.goto(url, wait_until='networkidle', timeout=60000)
                except PlaywrightTimeoutError:
                    logger.warning(f"Page load timeout on page {page_num}, continuing...")

                # Wait for Cloudflare (only needed on first page usually)
                if page_num == 1:
                    await self.wait_for_cloudflare()

                # Wait a moment for dynamic content
                await asyncio.sleep(2)

                # Get page HTML
                html = await self.page.content()

                # Parse listings
                listings = self._parse_page(html)
                all_listings.extend(listings)

                logger.info(f"Page {page_num}: Found {len(listings)} listings (Total: {len(all_listings)})")

                # Rate limiting - be respectful
                if page_num < max_pages:
                    delay = Config.SCRAPE_DELAY_SECONDS
                    logger.debug(f"Waiting {delay}s before next page...")
                    await asyncio.sleep(delay)

        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)

        finally:
            logger.info(f"Scraping complete. Total listings: {len(all_listings)}")

        return all_listings

    def _parse_page(self, html: str) -> List[Dict]:
        """Parse HTML and extract listings from __NEXT_DATA__ JSON"""
        soup = BeautifulSoup(html, 'lxml')
        listings = []

        # Try to extract __NEXT_DATA__ JSON (much more reliable!)
        next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})

        if next_data_script and next_data_script.string:
            try:
                data = json.loads(next_data_script.string)

                # Navigate to listings array
                page_props = data.get('props', {}).get('pageProps', {})
                listings_data = page_props.get('listings', [])

                logger.info(f"Found {len(listings_data)} listings in __NEXT_DATA__")

                for item in listings_data:
                    listing = self._parse_listing_json(item.get('listing', {}))
                    if listing:
                        listings.append(listing)

                return listings

            except Exception as e:
                logger.warning(f"Failed to parse __NEXT_DATA__: {e}, falling back to HTML parsing")

        # Fallback: Try HTML parsing if JSON extraction fails
        logger.warning("__NEXT_DATA__ not found, trying HTML parsing")
        cards = (
            soup.find_all('div', {'data-testid': 'search-result'}) or
            soup.find_all('div', {'data-testid': 'listing'}) or
            soup.find_all('a', href=re.compile(r'/for-rent/.*/\d+'))
        )

        if not cards:
            logger.warning("No listing cards found on page")
            return []

        for card in cards:
            listing = self._parse_listing_card(card)
            if listing:
                listings.append(listing)

        return listings

    def _parse_listing_json(self, listing_data: Dict) -> Optional[Dict]:
        """Extract all data from JSON listing object"""
        try:
            # Extract coordinates
            coordinates = listing_data.get('point', {}).get('coordinates', [])
            longitude = coordinates[0] if len(coordinates) > 0 else None
            latitude = coordinates[1] if len(coordinates) > 1 else None

            # Extract seller info
            seller = listing_data.get('seller', {})

            # Extract media info
            media = listing_data.get('media', {})

            # Extract BER info
            ber = listing_data.get('ber', {})

            # Parse price
            price_text = listing_data.get('abbreviatedPrice', listing_data.get('price'))
            price = self._parse_price(price_text)

            # Parse bedrooms
            bedrooms_text = listing_data.get('numBedrooms')
            bedrooms = self._parse_number(bedrooms_text)

            # Extract county from title
            title = listing_data.get('title')
            county = self._extract_county(title) if title else None

            # Build complete listing object with ALL fields
            return {
                # Basic info
                'property_id': listing_data.get('id'),
                'daft_shortcode': listing_data.get('daftShortcode'),
                'title': title,
                'seo_title': listing_data.get('seoTitle'),
                'price': price,
                'price_raw': listing_data.get('price'),
                'abbreviated_price': listing_data.get('abbreviatedPrice'),

                # Property details
                'property_type': listing_data.get('propertyType'),
                'bedrooms': bedrooms,
                'num_bedrooms_raw': bedrooms_text,
                'county': county,
                'sections': ','.join(listing_data.get('sections', [])),
                'sale_type': ','.join(listing_data.get('saleType', [])),

                # Dates and status
                'publish_date': listing_data.get('publishDate'),
                'date_of_construction': listing_data.get('dateOfConstruction'),
                'category': listing_data.get('category'),
                'state': listing_data.get('state'),

                # Featured info
                'featured_level': listing_data.get('featuredLevel'),
                'featured_level_full': listing_data.get('featuredLevelFull'),
                'premier_partner': listing_data.get('premierPartner'),

                # Location
                'latitude': latitude,
                'longitude': longitude,
                'seo_friendly_path': listing_data.get('seoFriendlyPath'),

                # Seller info
                'seller_id': seller.get('sellerId'),
                'seller_name': seller.get('name'),
                'seller_phone': seller.get('phone'),
                'seller_branch': seller.get('branch'),
                'seller_type': seller.get('sellerType'),
                'licence_number': seller.get('licenceNumber'),

                # Media
                'total_images': media.get('totalImages'),
                'has_video': media.get('hasVideo'),
                'has_virtual_tour': media.get('hasVirtualTour'),
                'has_brochure': media.get('hasBrochure'),

                # Energy rating
                'ber_rating': ber.get('rating'),

                # PRS info (if applicable)
                'prs_total_unit_types': listing_data.get('prs', {}).get('totalUnitTypes'),
                'prs_tagline': listing_data.get('prs', {}).get('tagLine'),

                # URL
                'property_url': f"{self.base_url}{listing_data.get('seoFriendlyPath')}" if listing_data.get('seoFriendlyPath') else None,

                # Scraping metadata
                'scraped_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error parsing JSON listing: {e}", exc_info=True)
            return None

    def _parse_listing_card(self, card) -> Optional[Dict]:
        """Extract data from individual listing card"""
        try:
            # Extract link
            link = card.find('a', href=True)
            if not link:
                link = card if card.name == 'a' else None

            property_url = link['href'] if link else None
            property_id = self._extract_property_id(property_url)

            # Extract price
            price_elem = (
                card.find('span', {'data-testid': 'price'}) or
                card.find('div', {'data-testid': 'price'}) or
                card.find(class_=lambda x: x and 'price' in x.lower()) or
                card.find(string=re.compile(r'€\s*\d'))
            )

            price_text = None
            if price_elem:
                price_text = price_elem.text if hasattr(price_elem, 'text') else str(price_elem)
            price = self._parse_price(price_text)

            # Extract title/address
            title_elem = (
                card.find('h2') or
                card.find('h3') or
                card.find('div', {'data-testid': 'title'}) or
                card.find(class_=lambda x: x and 'title' in x.lower())
            )
            title = title_elem.text.strip() if title_elem else None

            # Extract bedrooms
            bedrooms_elem = (
                card.find(string=re.compile(r'\d+\s*bed', re.IGNORECASE)) or
                card.find('span', {'data-testid': 'beds'})
            )
            bedrooms_text = bedrooms_elem.text if hasattr(bedrooms_elem, 'text') else str(bedrooms_elem) if bedrooms_elem else None
            bedrooms = self._parse_number(bedrooms_text)

            # Extract property type
            property_type_elem = card.find('span', {'data-testid': 'property-type'})
            property_type = property_type_elem.text.strip() if property_type_elem else None

            # Extract county
            county = self._extract_county(title) if title else None

            # Only return if we got meaningful data
            if price or title:
                return {
                    'property_id': property_id,
                    'price': price,
                    'title': title,
                    'county': county,
                    'bedrooms': bedrooms,
                    'property_type': property_type,
                    'property_url': f"{self.base_url}{property_url}" if property_url and not property_url.startswith('http') else property_url,
                    'date_scraped': datetime.now(),
                    'source': 'daft.ie'
                }

            return None

        except Exception as e:
            logger.debug(f"Error parsing card: {e}")
            return None

    def _extract_property_id(self, url: Optional[str]) -> Optional[str]:
        """Extract property ID from URL"""
        if not url:
            return None
        match = re.search(r'/(\d+)/?$', url)
        return match.group(1) if match else None

    def _parse_price(self, price_text: Optional[str]) -> Optional[float]:
        """Parse price string to float"""
        if not price_text:
            return None
        clean_price = re.sub(r'[€,]', '', price_text)
        clean_price = re.search(r'([\d\.]+)', clean_price)
        if clean_price:
            try:
                return float(clean_price.group(1))
            except ValueError:
                return None
        return None

    def _parse_number(self, text: Optional[str]) -> Optional[int]:
        """Extract number from text"""
        if not text:
            return None
        match = re.search(r'\d+', text)
        return int(match.group()) if match else None

    def _extract_county(self, address: Optional[str]) -> Optional[str]:
        """Extract county from address string"""
        if not address:
            return None

        counties = [
            'Dublin', 'Cork', 'Galway', 'Limerick', 'Waterford', 'Kilkenny',
            'Wexford', 'Carlow', 'Kildare', 'Meath', 'Louth', 'Wicklow',
            'Offaly', 'Laois', 'Westmeath', 'Longford', 'Kerry', 'Clare',
            'Tipperary', 'Sligo', 'Leitrim', 'Roscommon', 'Mayo', 'Donegal',
            'Cavan', 'Monaghan'
        ]

        address_upper = address.upper()
        for county in counties:
            if county.upper() in address_upper:
                return county

        county_match = re.search(r'(?:County|Co\.?)\s+([A-Za-z]+)', address, re.IGNORECASE)
        if county_match:
            return county_match.group(1).title()

        return None


    # ============================================================================
    # INCREMENTAL LOADING METHODS
    # ============================================================================

    def get_last_checkpoint(self) -> Optional[Dict]:
        """Get the last successful scrape checkpoint for Daft data"""
        try:
            query = """
                SELECT last_scraped_at, last_property_id, last_publish_date, total_records_scraped
                FROM scraping_checkpoints
                WHERE data_source = 'daft' AND status = 'completed'
                ORDER BY last_scraped_at DESC
                LIMIT 1
            """
            result = db.execute_query(query)
            return result[0] if result else None
        except Exception as e:
            logger.warning(f"Could not retrieve checkpoint: {e}")
            return None

    def update_checkpoint(self, last_property_id: str = None, last_publish_date: int = None,
                         total_records: int = 0, status: str = 'completed', error_msg: str = None):
        """Update the scraping checkpoint"""
        try:
            # Upsert checkpoint
            query = """
                INSERT INTO scraping_checkpoints
                (data_source, last_scraped_at, last_property_id, last_publish_date,
                 total_records_scraped, status, error_message)
                VALUES (%s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s)
                ON CONFLICT (data_source)
                DO UPDATE SET
                    last_scraped_at = CURRENT_TIMESTAMP,
                    last_property_id = EXCLUDED.last_property_id,
                    last_publish_date = EXCLUDED.last_publish_date,
                    total_records_scraped = EXCLUDED.total_records_scraped,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message
            """
            db.execute_sql(query, ('daft', last_property_id, last_publish_date,
                                 total_records, status, error_msg))
            logger.info(f"Updated checkpoint: status={status}, records={total_records}")
        except Exception as e:
            logger.error(f"Failed to update checkpoint: {e}")

    def should_do_full_load(self) -> bool:
        """Determine if we should do a full load or incremental load"""
        try:
            # Check if we have any Daft data
            query = "SELECT COUNT(*) as count FROM raw_daft_listings"
            result = db.execute_query(query)
            has_data = result[0]['count'] > 0 if result else False

            # Check if we have a valid checkpoint
            checkpoint = self.get_last_checkpoint()
            has_checkpoint = checkpoint is not None

            # If no data exists, do full load
            if not has_data:
                logger.info("No existing data found - performing full load")
                return True

            # If we have data but no checkpoint, assume we need full load to establish baseline
            if not has_checkpoint:
                logger.info("No checkpoint found - performing full load to establish baseline")
                return True

            # Otherwise, do incremental load
            logger.info("Existing data and checkpoint found - performing incremental load")
            return False

        except Exception as e:
            logger.warning(f"Could not determine load type: {e} - defaulting to full load")
            return True

    async def scrape_listings_incremental(self, max_pages_incremental: int = 5) -> List[Dict]:
        """
        Smart scraping that does full load initially, then incremental loads

        Args:
            max_pages_incremental: Maximum pages to scrape for incremental loads

        Returns:
            List of property dictionaries
        """
        if self.should_do_full_load():
            logger.info("🔄 PERFORMING FULL LOAD - Getting ALL historical data from Daft.ie")
            # For full load, scrape ALL available pages to get complete dataset
            listings = await self.scrape_all_listings(max_pages=1000)  # Safety limit of 1000 pages

            if listings:
                # Update checkpoint with the latest data
                latest_listing = max(listings, key=lambda x: x.get('publish_date', 0) or 0)
                self.update_checkpoint(
                    last_property_id=latest_listing.get('property_id'),
                    last_publish_date=latest_listing.get('publish_date'),
                    total_records=len(listings),
                    status='completed'
                )
                logger.info(f"✅ Full load completed: {len(listings)} total listings, checkpoint saved")
        else:
            logger.info("🔄 PERFORMING INCREMENTAL LOAD - Getting only new data")
            checkpoint = self.get_last_checkpoint()
            last_publish_date = checkpoint.get('last_publish_date') if checkpoint else None

            # For incremental load, scrape fewer pages but filter for new data
            all_listings = await self.scrape_listings(max_pages=max_pages_incremental)

            # Filter to only newer listings than our checkpoint
            if last_publish_date:
                new_listings = [
                    listing for listing in all_listings
                    if (listing.get('publish_date') or 0) > last_publish_date
                ]
                logger.info(f"🔍 Filtered {len(all_listings)} scraped listings to {len(new_listings)} new listings")
                listings = new_listings
            else:
                listings = all_listings

            if listings:
                # Update checkpoint
                latest_listing = max(listings, key=lambda x: x.get('publish_date', 0) or 0)
                total_scraped = checkpoint.get('total_records_scraped', 0) + len(listings) if checkpoint else len(listings)
                self.update_checkpoint(
                    last_property_id=latest_listing.get('property_id'),
                    last_publish_date=latest_listing.get('publish_date'),
                    total_records=total_scraped,
                    status='completed'
                )
                logger.info(f"✅ Incremental load completed: {len(listings)} new listings")
            else:
                logger.info("ℹ️  No new listings found")

        return listings


async def main():
    """Main function to run automated scraper"""
    """Main function to run automated scraper"""
    logger.info("Starting automated Daft scraper")

    # Use async context manager for automatic cleanup
    async with DaftScraperAutomatedAsync(headless=True) as scraper:
        listings = await scraper.scrape_listings(max_pages=3)

    logger.info(f"Scraped {len(listings)} total listings")
    return listings


if __name__ == "__main__":
    asyncio.run(main())
