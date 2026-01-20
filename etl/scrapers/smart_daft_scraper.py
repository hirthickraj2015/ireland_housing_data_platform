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
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='Europe/Dublin',
        )

        await self.context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        })

        self.page = await self.context.new_page()
        logger.info("Browser started successfully")

    async def wait_for_cloudflare(self, timeout: int = 30000):
        """Wait for Cloudflare challenge to complete"""
        logger.info("Waiting for Cloudflare challenge...")
        try:
            await self.page.wait_for_selector(
                'div[data-testid="search-result"], a[href*="/for-rent/"]',
                timeout=timeout,
                state='visible'
            )
            logger.info("Cloudflare challenge passed!")
            return True
        except Exception:
            logger.warning("Cloudflare challenge timeout - continuing anyway")
            return False

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

    async def scrape_rentals(self, max_pages: int = None) -> int:
        """
        Smart scraping with automatic full/incremental mode detection
        Loads data to database PAGE BY PAGE to avoid memory issues

        Args:
            max_pages: Maximum pages to scrape (None = scrape until no more listings found)

        Returns:
            Total number of listings loaded to database
        """
        # Determine strategy
        mode = self._determine_scraping_strategy()

        # Import loader here to avoid circular imports
        from etl.loaders.data_loader import DataLoader
        loader = DataLoader()

        page_num = 1
        consecutive_empty_pages = 0
        total_loaded = 0

        # OPTIMIZATION: In incremental mode with chronological sort, we can stop after first empty page
        # because all subsequent pages will be even older (since we sort by publishDateDesc)
        # In FULL mode, allow more empty pages to handle transient errors
        max_empty_pages = 1 if mode == 'incremental' else 5

        # For incremental mode, no need to check many pages due to chronological optimization
        if mode == 'incremental' and max_pages is None:
            max_pages = 10  # Reduced from 50 since we stop after first empty page
            logger.info(f"Incremental mode: Chronological sort enabled, will stop after first empty page")
        elif mode == 'full' and max_pages is None:
            logger.info(f"Full mode: Will scrape ALL available pages (stop after {max_empty_pages} consecutive empty pages)")

        while True:
            # Check if we should stop
            if max_pages and page_num > max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break

            if consecutive_empty_pages >= max_empty_pages:
                if mode == 'incremental':
                    logger.info(f"Found {consecutive_empty_pages} empty page(s) with no new listings, stopping")
                    logger.info("   ⚡ Since listings are sorted chronologically (newest first), all remaining pages are older")
                else:
                    logger.info(f"Found {consecutive_empty_pages} consecutive pages with no listings (errors or end of results)")
                break

            # Progress logging every 10 pages
            if page_num % 10 == 0:
                logger.info(f"📊 Progress: Page {page_num} | Loaded {total_loaded} listings so far")

            logger.info(f"Scraping page {page_num}...")

            # Build URL with pageSize and sort by publish_date descending (newest first)
            # NOTE: Daft.ie API does NOT support timestamp filtering parameters
            # We rely on chronological sort + client-side filtering + early stopping
            from_param = (page_num - 1) * 20
            url = f"{self.base_url}/property-for-rent/ireland?pageSize=20&from={from_param}&sort=publishDateDesc"

            try:
                # Navigate to page
                await self.page.goto(url, wait_until='networkidle', timeout=60000)

                # Wait for Cloudflare (only needed on first page usually)
                if page_num == 1:
                    await self.wait_for_cloudflare()

                # Wait for dynamic content
                await asyncio.sleep(2)

                # Get page content
                content = await self.page.content()

                # Parse listings
                listings = self._extract_listings_from_html(content)

                if not listings:
                    logger.warning(f"No listings found on page {page_num}")
                    consecutive_empty_pages += 1
                    page_num += 1
                    continue

                # In incremental mode: filter listings client-side by timestamp
                # (Daft.ie API doesn't support server-side timestamp filtering)
                if mode == 'incremental' and self.latest_publish_date:
                    # Client-side filter: only keep listings newer than checkpoint
                    new_listings = [
                        l for l in listings
                        if l.get('publish_date') and l['publish_date'] > self.latest_publish_date
                    ]

                    logger.info(f"Page {page_num}: Fetched {len(listings)} listings, {len(new_listings)} are new (after {self.latest_publish_date})")

                    if not new_listings:
                        consecutive_empty_pages += 1
                    else:
                        consecutive_empty_pages = 0
                        # LOAD TO DATABASE IMMEDIATELY (page by page)
                        rows_loaded = loader.load_daft_listings(new_listings)
                        total_loaded += rows_loaded
                        logger.info(f"💾 Loaded {rows_loaded} listings from page {page_num} to database")
                else:
                    # Full mode: take all listings
                    consecutive_empty_pages = 0
                    # LOAD TO DATABASE IMMEDIATELY (page by page)
                    rows_loaded = loader.load_daft_listings(listings)
                    total_loaded += rows_loaded
                    logger.info(f"Page {page_num}: API returned {len(listings)} listings")
                    logger.info(f"💾 Loaded {rows_loaded} listings from page {page_num} to database")

                page_num += 1

                # Slower in full mode to avoid rate limiting (3 seconds instead of 2)
                sleep_time = 3 if mode == 'full' else 2
                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {e}")
                consecutive_empty_pages += 1
                page_num += 1

                # Wait longer after errors to avoid rate limiting
                logger.info(f"Waiting 5 seconds before retry...")
                await asyncio.sleep(5)
                continue

        logger.info(f"✅ Scraping complete: {total_loaded} total listings loaded to database across {page_num-1} pages")
        return total_loaded

    def _extract_listings_from_html(self, html_content: str) -> List[Dict]:
        """Extract listings from HTML content"""
        soup = BeautifulSoup(html_content, 'lxml')
        listings = []

        # Try to find __NEXT_DATA__ script (most reliable method)
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})

        if script_tag and script_tag.string:
            try:
                data = json.loads(script_tag.string)
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

        # Fallback: HTML parsing if JSON extraction fails
        logger.warning("__NEXT_DATA__ not found, trying HTML parsing")
        cards = (
            soup.find_all('div', {'data-testid': 'search-result'}) or
            soup.find_all('div', {'data-testid': 'listing'}) or
            soup.find_all('a', href=re.compile(r'/for-rent/.*/\d+'))
        )

        if not cards:
            logger.warning("No listing cards found on page")
            return []

        logger.info(f"Found {len(cards)} listing cards via HTML parsing")

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
    """Main function to run the smart scraper with page-by-page loading"""
    logger.info("🚀 Starting Smart Daft Scraper")
    logger.info("=" * 70)

    async with SmartDaftScraper(headless=True) as scraper:
        # Scrape with automatic mode detection
        # Data is loaded to database PAGE BY PAGE inside scrape_rentals()
        total_loaded = await scraper.scrape_rentals(max_pages=None)

        if total_loaded > 0:
            logger.info(f"\n✅ Successfully loaded {total_loaded} listings to database (page by page)")
            logger.info("=" * 70)
            return True
        else:
            logger.info("ℹ️  No new listings found")
            logger.info("=" * 70)
            return True


if __name__ == "__main__":
    # Run the scraper
    asyncio.run(run_smart_scraper())
