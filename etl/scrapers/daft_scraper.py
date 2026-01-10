"""
Daft.ie Rental Listings Scraper
Extracts property rental data from Daft.ie
"""
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import re

from etl.config import Config
from etl.utils.logger import get_logger

logger = get_logger(__name__)


class DaftScraper:
    """Scraper for Daft.ie rental property listings"""

    def __init__(self):
        self.base_url = Config.DAFT_BASE_URL
        self.headers = {
            'User-Agent': Config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_listings(self, max_pages: int = 10) -> List[Dict]:
        """
        Scrape rental listings from Daft.ie

        Args:
            max_pages: Maximum number of pages to scrape

        Returns:
            List of property dictionaries
        """
        logger.info(f"Starting Daft.ie scrape for up to {max_pages} pages")
        all_listings = []

        for page in range(1, max_pages + 1):
            try:
                url = f"{self.base_url}/property-for-rent/ireland?pageSize=20&from={(page-1)*20}"
                logger.info(f"Scraping page {page}: {url}")

                response = self.session.get(
                    url,
                    timeout=Config.TIMEOUT_SECONDS
                )
                response.raise_for_status()

                listings = self._parse_page(response.text)
                all_listings.extend(listings)

                logger.info(f"Page {page}: Found {len(listings)} listings")

                # Respect rate limiting
                time.sleep(Config.SCRAPE_DELAY_SECONDS)

            except requests.RequestException as e:
                logger.error(f"Error scraping page {page}: {e}")
                continue

        logger.info(f"Scraping complete. Total listings: {len(all_listings)}")
        return all_listings

    def _parse_page(self, html: str) -> List[Dict]:
        """
        Parse HTML page and extract listing data

        Args:
            html: HTML content of the page

        Returns:
            List of parsed property dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        listings = []

        # Note: Daft.ie structure may change - this is a template
        # You'll need to inspect the actual HTML structure and adjust selectors
        property_cards = soup.find_all('div', {'data-testid': 'search-result'})

        for card in property_cards:
            try:
                listing = self._parse_listing_card(card)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"Error parsing listing card: {e}")
                continue

        return listings

    def _parse_listing_card(self, card) -> Optional[Dict]:
        """
        Parse individual listing card

        Args:
            card: BeautifulSoup element representing a property card

        Returns:
            Dictionary with property details
        """
        try:
            # Extract property ID from link
            link = card.find('a', href=True)
            property_url = link['href'] if link else None
            property_id = self._extract_property_id(property_url)

            # Extract price
            price_elem = card.find('span', {'data-testid': 'price'})
            price = self._parse_price(price_elem.text if price_elem else None)

            # Extract title and address
            title_elem = card.find('h2', {'data-testid': 'property-title'})
            title = title_elem.text.strip() if title_elem else None

            # Extract bedrooms
            bedrooms_elem = card.find('span', {'data-testid': 'beds'})
            bedrooms = self._parse_number(bedrooms_elem.text if bedrooms_elem else None)

            # Extract property type
            property_type_elem = card.find('span', {'data-testid': 'property-type'})
            property_type = property_type_elem.text.strip() if property_type_elem else None

            # Extract county from address
            county = self._extract_county(title)

            return {
                'property_id': property_id,
                'price': price,
                'title': title,
                'county': county,
                'bedrooms': bedrooms,
                'property_type': property_type,
                'property_url': f"{self.base_url}{property_url}" if property_url else None,
                'date_scraped': datetime.now(),
                'source': 'daft.ie'
            }

        except Exception as e:
            logger.warning(f"Error extracting listing details: {e}")
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
        # Remove currency symbols and commas
        clean_price = re.sub(r'[€,]', '', price_text)
        try:
            return float(clean_price)
        except ValueError:
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

        # Common Irish counties
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

        # Try to extract "County X" or "Co. X" pattern
        county_match = re.search(r'(?:County|Co\.?)\s+([A-Za-z]+)', address)
        if county_match:
            return county_match.group(1)

        return None


def main():
    """Main function to run the scraper"""
    scraper = DaftScraper()
    listings = scraper.scrape_listings(max_pages=5)

    logger.info(f"Scraped {len(listings)} total listings")
    return listings


if __name__ == "__main__":
    main()
