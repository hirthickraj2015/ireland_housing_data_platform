"""
Smart CSO Data Scraper with Dynamic Full/Incremental Loading
Automatically detects existing data and only fetches new records
"""
import requests
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
import io

from etl.utils.logger import get_logger
from etl.utils.database import db
from etl.loaders.data_loader import DataLoader

logger = get_logger(__name__)


class SmartCSOScraper:
    """
    Smart scraper for CSO datasets that automatically handles full vs incremental loads
    """

    BASE_URL = "https://data.cso.ie/api/data"

    # Dataset configurations
    DATASETS = {
        'rent': {
            'code': 'RIA02',
            'table': 'raw_cso_rent',
            'date_column': 'year',
            'description': 'Private Rent Index'
        },
        'cpi': {
            'code': 'CPA01',
            'table': 'raw_cso_cpi',
            'date_column': 'year',
            'description': 'Consumer Price Index'
        },
        'population': {
            'code': 'PEA01',
            'table': 'raw_cso_population',
            'date_column': 'year',
            'description': 'Population Estimates'
        },
        'income': {
            'code': 'CIA01',
            'table': 'raw_cso_income',
            'date_column': 'year',
            'description': 'Household Income'
        }
    }

    def __init__(self):
        self.loader = DataLoader()
        logger.info("Initialized Smart CSO Scraper")

    def _check_existing_data(self, dataset_key: str) -> tuple[bool, Optional[int]]:
        """
        Check if we have existing data for this dataset

        Returns:
            (has_data, latest_year)
        """
        dataset_info = self.DATASETS[dataset_key]
        table_name = dataset_info['table']
        date_column = dataset_info['date_column']

        try:
            query = f"""
                SELECT
                    COUNT(*) as count,
                    MAX({date_column}) as latest_year
                FROM {table_name}
                WHERE {date_column} IS NOT NULL
            """

            result = db.execute_query(query)

            if result and len(result) > 0:
                count = result[0].get('count', 0)
                latest_year = result[0].get('latest_year')

                has_data = count > 0

                logger.info(f"[{dataset_key.upper()}] Database check: {count} existing records")
                if latest_year:
                    logger.info(f"[{dataset_key.upper()}] Latest year in DB: {latest_year}")

                return has_data, latest_year

            return False, None

        except Exception as e:
            logger.warning(f"[{dataset_key.upper()}] Could not check existing data: {e}")
            return False, None

    def _fetch_cso_dataset(self, dataset_code: str) -> Optional[pd.DataFrame]:
        """
        Fetch complete dataset from CSO API

        Args:
            dataset_code: CSO dataset code (e.g., 'RIA02', 'CPA01')

        Returns:
            DataFrame with all available data
        """
        try:
            url = f"{self.BASE_URL}/{dataset_code}?format=csv"
            logger.info(f"Fetching from: {url}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Read CSV, handle BOM
            csv_content = response.content.decode('utf-8-sig')
            df = pd.read_csv(io.StringIO(csv_content))

            logger.info(f"Fetched {len(df)} records from {dataset_code}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch {dataset_code}: {e}")
            return None

    def scrape_dataset(self, dataset_key: str, force_full: bool = False) -> bool:
        """
        Smart scrape a specific CSO dataset with automatic mode detection

        Args:
            dataset_key: Key from DATASETS dict ('rent', 'cpi', 'population', 'income')
            force_full: Force full load even if data exists

        Returns:
            True if successful, False otherwise
        """
        dataset_info = self.DATASETS[dataset_key]
        dataset_code = dataset_info['code']
        description = dataset_info['description']

        logger.info(f"\n{'='*70}")
        logger.info(f"📊 Processing CSO Dataset: {description} ({dataset_code})")
        logger.info(f"{'='*70}")

        # Check for existing data
        has_data, latest_year = self._check_existing_data(dataset_key)

        if force_full:
            mode = 'full'
            logger.info("🔄 MODE: FULL LOAD (forced)")
        elif not has_data:
            mode = 'full'
            logger.info("🔄 MODE: FULL LOAD - No existing data found")
        else:
            mode = 'incremental'
            logger.info(f"⚡ MODE: INCREMENTAL LOAD - Will load data after {latest_year}")

        # Fetch data from CSO
        df = self._fetch_cso_dataset(dataset_code)

        if df is None or df.empty:
            logger.error(f"Failed to fetch {dataset_code}")
            return False

        # Filter for incremental mode
        if mode == 'incremental' and latest_year is not None:
            # Extract year from data
            if 'TIME_PERIOD' in df.columns:
                df['year'] = pd.to_numeric(df['TIME_PERIOD'].str[:4], errors='coerce')
                original_count = len(df)
                df = df[df['year'] > latest_year]
                new_count = len(df)
                logger.info(f"Filtered: {original_count} total records → {new_count} new records")

                if new_count == 0:
                    logger.info(f"ℹ️  No new data for {dataset_code}")
                    return True

        # Load into database
        logger.info(f"💾 Loading {len(df)} records into database...")

        try:
            if dataset_key == 'rent':
                success = self.loader.load_cso_rent(df)
            elif dataset_key == 'cpi':
                success = self.loader.load_cso_cpi(df)
            elif dataset_key == 'population':
                success = self.loader.load_cso_population(df)
            elif dataset_key == 'income':
                success = self.loader.load_cso_income(df)
            else:
                logger.error(f"Unknown dataset: {dataset_key}")
                return False

            if success:
                logger.info(f"✅ Successfully loaded {len(df)} records")
                return True
            else:
                logger.error(f"❌ Failed to load {dataset_key} data")
                return False

        except Exception as e:
            logger.error(f"Error loading {dataset_key}: {e}")
            return False

    def scrape_all_datasets(self, force_full: bool = False) -> Dict[str, bool]:
        """
        Scrape all CSO datasets with smart incremental loading

        Args:
            force_full: Force full load for all datasets

        Returns:
            Dictionary with results for each dataset
        """
        logger.info("\n" + "="*70)
        logger.info("🚀 Starting Smart CSO Data Collection")
        logger.info("="*70)

        results = {}

        for dataset_key in self.DATASETS.keys():
            try:
                success = self.scrape_dataset(dataset_key, force_full=force_full)
                results[dataset_key] = success
            except Exception as e:
                logger.error(f"Error processing {dataset_key}: {e}")
                results[dataset_key] = False

        # Summary
        logger.info("\n" + "="*70)
        logger.info("📊 CSO Data Collection Summary")
        logger.info("="*70)

        for dataset_key, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            dataset_name = self.DATASETS[dataset_key]['description']
            logger.info(f"{status}: {dataset_name}")

        successful = sum(1 for s in results.values() if s)
        total = len(results)
        logger.info(f"\nOverall: {successful}/{total} datasets processed successfully")
        logger.info("="*70)

        return results


def run_smart_cso_scraper(datasets: Optional[List[str]] = None, force_full: bool = False):
    """
    Main function to run the smart CSO scraper

    Args:
        datasets: List of dataset keys to scrape (None = all)
        force_full: Force full load
    """
    scraper = SmartCSOScraper()

    if datasets:
        # Scrape specific datasets
        results = {}
        for dataset in datasets:
            if dataset in scraper.DATASETS:
                results[dataset] = scraper.scrape_dataset(dataset, force_full=force_full)
            else:
                logger.error(f"Unknown dataset: {dataset}")
                logger.info(f"Available: {list(scraper.DATASETS.keys())}")
        return results
    else:
        # Scrape all datasets
        return scraper.scrape_all_datasets(force_full=force_full)


if __name__ == "__main__":
    # Run all CSO scrapers
    run_smart_cso_scraper()
