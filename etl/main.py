"""
Main ETL Pipeline Orchestrator
Runs all scrapers and loads data into PostgreSQL
"""
import sys
from datetime import datetime

from etl.scrapers.daft_scraper import DaftScraper
from etl.scrapers.cso_scraper import CSOScraper
from etl.scrapers.ecb_scraper import ECBScraper
from etl.scrapers.property_price_scraper import PropertyPriceScraper
from etl.loaders.data_loader import DataLoader
from etl.utils.logger import get_logger
from etl.config import Config

logger = get_logger(__name__)


class ETLPipeline:
    """Main ETL Pipeline orchestrator"""

    def __init__(self):
        self.daft_scraper = DaftScraper()
        self.cso_scraper = CSOScraper()
        self.ecb_scraper = ECBScraper()
        self.property_scraper = PropertyPriceScraper()
        self.loader = DataLoader()

    def run_full_pipeline(self):
        """Execute the complete ETL pipeline"""
        logger.info("=" * 80)
        logger.info("STARTING FULL ETL PIPELINE")
        logger.info(f"Timestamp: {datetime.now()}")
        logger.info("=" * 80)

        try:
            # Validate configuration
            Config.validate()
            logger.info("Configuration validated")

            # Step 1: Extract data from all sources
            logger.info("\n📡 EXTRACTION PHASE")
            data = self._extract_all_data()

            # Step 2: Load data into PostgreSQL
            logger.info("\n💾 LOADING PHASE")
            results = self._load_all_data(data)

            # Step 3: Summary
            logger.info("\n✅ PIPELINE COMPLETE")
            self._print_summary(results)

            return True

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return False

    def _extract_all_data(self) -> dict:
        """Extract data from all sources"""
        data = {}

        # 1. Daft.ie rental listings
        try:
            logger.info("Scraping Daft.ie rental listings...")
            data['daft_listings'] = self.daft_scraper.scrape_listings(max_pages=5)
            logger.info(f"✓ Daft: {len(data['daft_listings'])} listings scraped")
        except Exception as e:
            logger.error(f"✗ Daft scraping failed: {e}")
            data['daft_listings'] = []

        # 2. CSO datasets
        try:
            logger.info("Fetching CSO datasets...")
            cso_data = self.cso_scraper.fetch_all_datasets()
            data['cso_rent_index'] = cso_data.get('rent_index')
            data['cso_income'] = cso_data.get('disposable_income')
            data['cso_population'] = cso_data.get('population')
            data['cso_cpi'] = cso_data.get('cpi')
            logger.info(f"✓ CSO: {sum(len(df) for df in cso_data.values())} total records")
        except Exception as e:
            logger.error(f"✗ CSO fetching failed: {e}")
            data['cso_rent_index'] = None
            data['cso_income'] = None

        # 3. ECB interest rates
        try:
            logger.info("Fetching ECB interest rates...")
            ecb_data = self.ecb_scraper.fetch_interest_rates()
            data['ecb_rates'] = ecb_data
            logger.info(f"✓ ECB: {len(ecb_data)} rate records fetched")
        except Exception as e:
            logger.error(f"✗ ECB fetching failed: {e}")
            data['ecb_rates'] = None

        # 4. Property Price Register
        try:
            logger.info("Fetching Property Price Register data...")
            property_data = self.property_scraper.fetch_recent_sales(months=12)
            data['property_sales'] = property_data
            logger.info(f"✓ Property Register: {len(property_data)} sales fetched")
        except Exception as e:
            logger.error(f"✗ Property Register fetching failed: {e}")
            data['property_sales'] = None

        return data

    def _load_all_data(self, data: dict) -> dict:
        """Load all extracted data into database"""
        logger.info("Loading data into PostgreSQL...")

        results = self.loader.load_all_data(data)

        for dataset, row_count in results.items():
            logger.info(f"✓ {dataset}: {row_count} rows loaded")

        return results

    def _print_summary(self, results: dict):
        """Print pipeline execution summary"""
        total_rows = sum(results.values())

        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 80)

        for dataset, count in results.items():
            logger.info(f"{dataset:.<40} {count:>10} rows")

        logger.info("-" * 80)
        logger.info(f"{'TOTAL':.<40} {total_rows:>10} rows")
        logger.info("=" * 80)

    def run_scrapers_only(self):
        """Run only the scraping phase (no loading)"""
        logger.info("Running scrapers only (no database load)")
        data = self._extract_all_data()
        return data

    def run_specific_scraper(self, scraper_name: str):
        """Run a specific scraper"""
        scrapers = {
            'daft': lambda: self.daft_scraper.scrape_listings(),
            'cso': lambda: self.cso_scraper.fetch_all_datasets(),
            'ecb': lambda: self.ecb_scraper.fetch_interest_rates(),
            'property': lambda: self.property_scraper.fetch_recent_sales()
        }

        if scraper_name not in scrapers:
            logger.error(f"Unknown scraper: {scraper_name}")
            return None

        logger.info(f"Running {scraper_name} scraper")
        return scrapers[scraper_name]()


def main():
    """Main entry point"""
    pipeline = ETLPipeline()

    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'extract':
            # Run scrapers only
            data = pipeline.run_scrapers_only()
            logger.info("Extraction complete")

        elif command in ['daft', 'cso', 'ecb', 'property']:
            # Run specific scraper
            result = pipeline.run_specific_scraper(command)
            logger.info(f"{command} scraper complete")

        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Available commands: extract, daft, cso, ecb, property")
            sys.exit(1)
    else:
        # Run full pipeline
        success = pipeline.run_full_pipeline()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
