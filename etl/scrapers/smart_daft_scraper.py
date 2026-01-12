"""
Smart Daft.ie Scraper with Dynamic Full/Incremental Loading
Automatically detects if database is empty and switches between modes
"""
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from etl.config import Config
from etl.utils.logger import get_logger
from etl.utils.database import db
from etl.loaders.data_loader import DataLoader

logger = get_logger(__name__)


class SmartDaftScraper:
    """
    Smart scraper that automatically handles full vs incremental loads
    """

    def __init__(self, headless: bool = True):
        self.base_url = Config.DAFT_BASE_URL
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.mode = None  # Will be 'full' or 'incremental'
        self.latest_publish_date = None

        logger.info(f"Initialized Smart Daft scraper (headless={headless})")

    def _check_existing_data(self) -> tuple[bool, Optional[int]]:
        """
        Check if we have existing Daft data in database

        Returns:
            (has_data, latest_publish_date)
        """
        try:
            query = """
                SELECT
                    COUNT(*) as count,
                    MAX(publish_date) as latest_publish_date
                FROM raw_daft_listings
                WHERE publish_date IS NOT NULL
            """

            result = db.execute_query(query)

            if result and len(result) > 0:
                count = result[0].get('count', 0)
                latest_date = result[0].get('latest_publish_date')

                has_data = count > 0

                logger.info(f"Database check: {count} existing listings found")
                if latest_date:
                    logger.info(f"Latest publish_date in DB: {latest_date}")

                return has_data, latest_date

            return False, None

        except Exception as e:
            logger.warning(f"Could not check existing data: {e}. Defaulting to full load.")
            return False, None

    def _determine_scraping_strategy(self):
        """Automatically determine if we should do full or incremental load"""
        has_data, latest_publish_date = self._check_existing_data()

        if not has_data:
            self.mode = 'full'
            self.latest_publish_date = None
            logger.info("🔄 MODE: FULL LOAD - No existing data found, will scrape all available listings")
        else:
            self.mode = 'incremental'
            self.latest_publish_date = latest_publish_date
            logger.info(f"⚡ MODE: INCREMENTAL LOAD - Will scrape only listings after {latest_publish_date}")

        return self.mode

    async def __aenter__(self):
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_browser()

    async def start_browser(self):
        """Start Playwright browser"""
        logger.info("Starting browser...")

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            locale='en-US',
            timezone_id='Europe/Dublin',
        )

        await self.context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

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

    async def scrape_rentals(self, max_pages: int = None) -> List[Dict]:
        """
        Smart scraping with automatic full/incremental mode detection

        Args:
            max_pages: Maximum pages to scrape (None = scrape until no more listings found)

        Returns:
            List of new listing dictionaries
        """
        # Determine strategy
        mode = self._determine_scraping_strategy()

        all_listings = []
        page_num = 1
        consecutive_empty_pages = 0
        new_listings_count = 0

        # For incremental mode, limit pages to recent listings
        if mode == 'incremental' and max_pages is None:
            max_pages = 5  # Only check first 5 pages for new listings
            logger.info("Incremental mode: Will check first 5 pages for new listings")

        while True:
            # Check if we should stop
            if max_pages and page_num > max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break

            if consecutive_empty_pages >= 2:
                logger.info("Found 2 consecutive pages with no new listings, stopping")
                break

            logger.info(f"Scraping page {page_num}...")

            # Build URL
            from_param = (page_num - 1) * 20
            url = f"{self.base_url}/property-for-rent/ireland?from={from_param}"

            try:
                # Navigate to page
                await self.page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)  # Let JavaScript render

                # Get page content
                content = await self.page.content()

                # Parse listings
                listings = self._extract_listings_from_html(content)

                if not listings:
                    logger.warning(f"No listings found on page {page_num}")
                    consecutive_empty_pages += 1
                    page_num += 1
                    continue

                # Filter listings based on mode
                if mode == 'incremental' and self.latest_publish_date:
                    # Only keep listings newer than what we have
                    new_listings = [
                        l for l in listings
                        if l.get('publish_date') and l['publish_date'] > self.latest_publish_date
                    ]

                    logger.info(f"Page {page_num}: Found {len(listings)} listings, {len(new_listings)} are new")

                    if not new_listings:
                        consecutive_empty_pages += 1
                    else:
                        consecutive_empty_pages = 0
                        all_listings.extend(new_listings)
                        new_listings_count += len(new_listings)
                else:
                    # Full mode: take all listings
                    all_listings.extend(listings)
                    new_listings_count += len(listings)
                    consecutive_empty_pages = 0
                    logger.info(f"Page {page_num}: Found {len(listings)} listings")

                page_num += 1
                await asyncio.sleep(2)  # Be nice to the server

            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {e}")
                consecutive_empty_pages += 1
                page_num += 1
                continue

        logger.info(f"✅ Scraping complete: {new_listings_count} new listings found across {page_num-1} pages")
        return all_listings

    def _extract_listings_from_html(self, html_content: str) -> List[Dict]:
        """Extract listings from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = []

        # Try to find __NEXT_DATA__ script
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})

        if script_tag:
            try:
                data = json.loads(script_tag.string)
                page_props = data.get('props', {}).get('pageProps', {})
                listings_data = page_props.get('listings', [])

                for item in listings_data:
                    listing = self._parse_listing_json(item.get('listing', {}))
                    if listing:
                        listings.append(listing)

                return listings
            except Exception as e:
                logger.warning(f"Failed to parse __NEXT_DATA__: {e}")

        # Fallback: HTML parsing
        cards = soup.find_all('div', {'data-testid': 'search-result'})
        for card in cards:
            listing = self._parse_listing_card(card)
            if listing:
                listings.append(listing)

        return listings

    def _parse_listing_json(self, listing_data: Dict) -> Optional[Dict]:
        """Extract all data from JSON listing object"""
        try:
            coordinates = listing_data.get('point', {}).get('coordinates', [])
            longitude = coordinates[0] if len(coordinates) > 0 else None
            latitude = coordinates[1] if len(coordinates) > 1 else None

            seller = listing_data.get('seller', {})
            media = listing_data.get('media', {})
            ber = listing_data.get('ber', {})

            price_text = listing_data.get('abbreviatedPrice', listing_data.get('price'))
            price = self._parse_price(price_text)

            bedrooms_text = listing_data.get('numBedrooms')
            bedrooms = self._parse_number(bedrooms_text)

            title = listing_data.get('title')
            county = self._extract_county(title) if title else None

            return {
                'property_id': listing_data.get('id'),
                'daft_shortcode': listing_data.get('daftShortcode'),
                'title': title,
                'seo_title': listing_data.get('seoTitle'),
                'price': price,
                'price_raw': listing_data.get('price'),
                'abbreviated_price': listing_data.get('abbreviatedPrice'),
                'property_type': listing_data.get('propertyType'),
                'bedrooms': bedrooms,
                'num_bedrooms_raw': bedrooms_text,
                'county': county,
                'sections': ','.join(listing_data.get('sections', [])),
                'sale_type': ','.join(listing_data.get('saleType', [])),
                'publish_date': listing_data.get('publishDate'),
                'date_of_construction': listing_data.get('dateOfConstruction'),
                'category': listing_data.get('category'),
                'state': listing_data.get('state'),
                'featured_level': listing_data.get('featuredLevel'),
                'featured_level_full': listing_data.get('featuredLevelFull'),
                'premier_partner': listing_data.get('premierPartner'),
                'latitude': latitude,
                'longitude': longitude,
                'seo_friendly_path': listing_data.get('seoFriendlyPath'),
                'seller_id': seller.get('sellerId'),
                'seller_name': seller.get('name'),
                'seller_phone': seller.get('phone'),
                'seller_branch': seller.get('branch'),
                'seller_type': seller.get('sellerType'),
                'licence_number': seller.get('licenceNumber'),
                'total_images': media.get('totalImages'),
                'has_video': media.get('hasVideo'),
                'has_virtual_tour': media.get('hasVirtualTour'),
                'has_brochure': media.get('hasBrochure'),
                'ber_rating': ber.get('rating'),
                'prs_total_unit_types': listing_data.get('prsTotalUnitTypes'),
                'prs_tagline': listing_data.get('prsTagline'),
                'property_url': f"https://www.daft.ie{listing_data.get('seoFriendlyPath', '')}",
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing listing JSON: {e}")
            return None

    def _parse_listing_card(self, card) -> Optional[Dict]:
        """Fallback HTML parsing"""
        try:
            return {
                'property_id': None,
                'title': card.get_text(strip=True)[:200] if card else None,
                'scraped_at': datetime.now().isoformat()
            }
        except:
            return None

    def _parse_price(self, price_text) -> Optional[float]:
        """Parse price from text"""
        if not price_text:
            return None
        try:
            price_str = str(price_text).replace('€', '').replace(',', '').strip()
            return float(re.sub(r'[^\d.]', '', price_str))
        except:
            return None

    def _parse_number(self, text) -> Optional[int]:
        """Parse number from text"""
        if not text:
            return None
        try:
            return int(re.sub(r'[^\d]', '', str(text)))
        except:
            return None

    def _extract_county(self, title: str) -> Optional[str]:
        """Extract county from title"""
        if not title:
            return None

        irish_counties = [
            'Dublin', 'Cork', 'Galway', 'Limerick', 'Waterford', 'Kilkenny',
            'Wexford', 'Carlow', 'Kildare', 'Meath', 'Louth', 'Wicklow',
            'Offaly', 'Laois', 'Westmeath', 'Longford', 'Roscommon', 'Sligo',
            'Leitrim', 'Donegal', 'Mayo', 'Kerry', 'Clare', 'Tipperary',
            'Cavan', 'Monaghan'
        ]

        title_upper = title.upper()
        for county in irish_counties:
            if county.upper() in title_upper:
                return county

        return None


async def run_smart_scraper():
    """Main function to run the smart scraper"""
    logger.info("🚀 Starting Smart Daft Scraper")
    logger.info("=" * 70)

    async with SmartDaftScraper(headless=True) as scraper:
        # Scrape with automatic mode detection
        listings = await scraper.scrape_rentals(max_pages=None)

        if listings:
            logger.info(f"\n📊 Scraped {len(listings)} new listings")
            logger.info("💾 Loading into database...")

            # Load into database
            loader = DataLoader()
            success = loader.load_daft_listings(listings)

            if success:
                logger.info(f"✅ Successfully loaded {len(listings)} listings to database")
                logger.info("=" * 70)
                return True
            else:
                logger.error("❌ Failed to load some listings")
                return False
        else:
            logger.info("ℹ️  No new listings found")
            logger.info("=" * 70)
            return True


if __name__ == "__main__":
    # Run the scraper
    asyncio.run(run_smart_scraper())
