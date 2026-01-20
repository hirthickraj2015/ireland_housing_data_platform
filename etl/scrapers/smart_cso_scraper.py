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
    Uses the statbank.cso.ie API with JSON-stat format
    """

    # PxStat API endpoint (JSON-stat 2.0 format)
    BASE_URL = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset"

    # Dataset configurations with StatBank table IDs
    DATASETS = {
        'rent': {
            'code': 'RIA02',  # RTB Rent Index by Year, Type of Accommodation and County
            'table': 'raw_cso_rent',
            'date_column': 'year',
            'description': 'RTB Private Rent Index'
        },
        'cpi': {
            'code': 'CPM01',  # Consumer Price Index
            'table': 'raw_cso_cpi',
            'date_column': 'year',
            'description': 'Consumer Price Index'
        },
        'population': {
            'code': 'PEA01',  # Population Estimates
            'table': 'raw_cso_population',
            'date_column': 'year',
            'description': 'Population Estimates'
        },
        'income': {
            'code': 'CIA01',  # County Incomes and Regional GDP
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

    def _fetch_cso_dataset(self, dataset_code: str, api_method: str = None) -> Optional[pd.DataFrame]:
        """
        Fetch complete dataset from CSO PxStat API

        Args:
            dataset_code: CSO dataset code (e.g., 'RIA02', 'CPM01')
            api_method: Deprecated parameter, kept for backwards compatibility

        Returns:
            DataFrame with all available data
        """
        try:
            # PxStat API: JSON-stat 2.0 format
            url = f"{self.BASE_URL}/{dataset_code}/JSON-stat/2.0/en"
            logger.info(f"Fetching from PxStat API: {url}")

            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (compatible; Ireland Housing Data Platform/1.0)'
            }

            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()

            # Parse JSON-stat format
            data = response.json()

            # Convert JSON-stat to DataFrame
            df = self._parse_jsonstat(data)

            if df is not None and not df.empty:
                logger.info(f"Fetched {len(df)} records from {dataset_code}")
                return df
            else:
                logger.warning(f"No data in response from {dataset_code}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch {dataset_code}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _parse_jsonstat(self, json_data: dict) -> Optional[pd.DataFrame]:
        """
        Parse JSON-stat 2.0 format response from PxStat API

        Args:
            json_data: JSON response from PxStat API

        Returns:
            DataFrame with parsed data
        """
        try:
            # JSON-stat 2.0 structure
            if 'dimension' not in json_data or 'value' not in json_data:
                logger.error("Invalid JSON-stat format: missing dimension or value")
                return None

            dimensions = json_data['dimension']
            values = json_data['value']

            # Get dimension metadata
            dim_roles = json_data.get('role', {})
            dim_ids = json_data.get('id', [])

            # Get size array to understand data structure
            sizes = json_data.get('size', [])

            # Build list of dimension info
            dim_info = []
            for dim_id in dim_ids:
                dim = dimensions[dim_id]
                categories = dim.get('category', {})
                cat_index = categories.get('index', [])
                cat_labels = categories.get('label', {})

                # Get category values in order
                if isinstance(cat_index, list):
                    cat_values = cat_index
                else:
                    # cat_index is a dict mapping values to positions
                    cat_values = sorted(cat_index.keys(), key=lambda x: cat_index[x])

                dim_info.append({
                    'id': dim_id,
                    'label': dim.get('label', dim_id),
                    'values': cat_values,
                    'labels': {v: cat_labels.get(v, v) for v in cat_values}
                })

            # Generate all combinations
            import itertools
            import numpy as np

            # Create cartesian product
            all_combos = list(itertools.product(*[d['values'] for d in dim_info]))

            # Build rows
            rows = []
            for idx, combo in enumerate(all_combos):
                if idx < len(values):
                    row = {}
                    for dim_idx, value in enumerate(combo):
                        dim = dim_info[dim_idx]
                        # Use both ID and label
                        row[dim['id']] = value
                        row[f"{dim['id']}_Label"] = dim['labels'].get(value, value)

                    # Add the metric value
                    row['VALUE'] = values[idx]
                    rows.append(row)

            df = pd.DataFrame(rows)

            # Clean up column names and extract year
            if 'TLIST(A1)' in df.columns:
                # Annual data - extract year directly
                df['Year'] = pd.to_numeric(df['TLIST(A1)'], errors='coerce').astype('Int64')
            elif 'TLIST(M1)' in df.columns:
                # Monthly data - extract year from YYYYMM format
                df['Year'] = df['TLIST(M1)'].astype(str).str[:4]
                df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')
            elif 'TLIST(Q1)' in df.columns:
                # Quarterly data - extract year from format like "2024Q1"
                df['Year'] = df['TLIST(Q1)'].astype(str).str[:4]
                df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')

            logger.info(f"Parsed JSON-stat: {len(df)} rows, {len(df.columns)} columns")
            logger.info(f"Columns: {list(df.columns)}")

            return df

        except Exception as e:
            logger.error(f"Error parsing JSON-stat format: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
        api_method = dataset_info.get('api_method', 'responseinstance')
        df = self._fetch_cso_dataset(dataset_code, api_method)

        if df is None or df.empty:
            logger.error(f"Failed to fetch {dataset_code}")
            return False

        # Filter for incremental mode
        if mode == 'incremental' and latest_year is not None:
            # Use the Year column already extracted by JSON-stat parser
            if 'Year' in df.columns:
                original_count = len(df)
                df = df[df['Year'] > latest_year]
                new_count = len(df)
                logger.info(f"Filtered: {original_count} total records → {new_count} new records (year > {latest_year})")

                if new_count == 0:
                    logger.info(f"ℹ️  No new data for {dataset_code} - database is up to date!")
                    return True
            elif 'TIME_PERIOD' in df.columns:
                # Fallback for CSV format
                df['year'] = pd.to_numeric(df['TIME_PERIOD'].str[:4], errors='coerce')
                original_count = len(df)
                df = df[df['year'] > latest_year]
                new_count = len(df)
                logger.info(f"Filtered: {original_count} total records → {new_count} new records")

                if new_count == 0:
                    logger.info(f"ℹ️  No new data for {dataset_code} - database is up to date!")
                    return True

        # Load into database
        logger.info(f"💾 Loading {len(df)} records into database...")

        try:
            if dataset_key == 'rent':
                rows_loaded = self.loader.load_cso_rent(df)
            elif dataset_key == 'cpi':
                rows_loaded = self.loader.load_cso_cpi(df)
            elif dataset_key == 'population':
                rows_loaded = self.loader.load_cso_population(df)
            elif dataset_key == 'income':
                rows_loaded = self.loader.load_cso_income(df)
            else:
                logger.error(f"Unknown dataset: {dataset_key}")
                return False

            # rows_loaded is the number of rows inserted (can be 0 if all duplicates)
            if rows_loaded == 0:
                logger.info(f"ℹ️  No new records inserted (all records already exist in database)")
                return True
            else:
                logger.info(f"✅ Successfully loaded {rows_loaded} new records")
                return True

        except Exception as e:
            logger.error(f"❌ Error loading {dataset_key}: {e}")
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
