"""
Data Loader - Loads scraped data into PostgreSQL raw tables
"""
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any

from etl.utils.database import db
from etl.utils.logger import get_logger

logger = get_logger(__name__)


class DataLoader:
    """Handles loading of raw data into PostgreSQL"""

    def __init__(self):
        self.db = db

    def load_daft_listings(self, listings: List[Dict]) -> int:
        """
        Load Daft.ie rental listings into raw_daft_listings table

        Args:
            listings: List of property listing dictionaries

        Returns:
            Number of rows inserted
        """
        if not listings:
            logger.warning("No Daft listings to load")
            return 0

        logger.info(f"Loading {len(listings)} Daft listings")

        # Convert to DataFrame
        df = pd.DataFrame(listings)

        # Ensure consistent column names and types
        df['date_scraped'] = pd.to_datetime(df.get('date_scraped', datetime.now()))
        df['price'] = pd.to_numeric(df.get('price'), errors='coerce')
        df['bedrooms'] = pd.to_numeric(df.get('bedrooms'), errors='coerce')

        # Load to database
        rows_loaded = self.db.load_dataframe(
            df=df,
            table='raw_daft_listings',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} Daft listings to raw_daft_listings")
        return rows_loaded

    def load_cso_rent_index(self, df: pd.DataFrame) -> int:
        """
        Load CSO Rent Index data

        Args:
            df: DataFrame with rent index data

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO rent index data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO rent index records")

        rows_loaded = self.db.load_dataframe(
            df=df,
            table='raw_cso_rent',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_cso_rent")
        return rows_loaded

    def load_cso_income(self, df: pd.DataFrame) -> int:
        """
        Load CSO disposable income data

        Args:
            df: DataFrame with income data

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO income data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO income records")

        rows_loaded = self.db.load_dataframe(
            df=df,
            table='raw_cso_income',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_cso_income")
        return rows_loaded

    def load_property_sales(self, df: pd.DataFrame) -> int:
        """
        Load Property Price Register data

        Args:
            df: DataFrame with property sale data

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No property sales data to load")
            return 0

        logger.info(f"Loading {len(df)} property sale records")

        rows_loaded = self.db.load_dataframe(
            df=df,
            table='raw_property_sales',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_property_sales")
        return rows_loaded

    def load_ecb_rates(self, df: pd.DataFrame) -> int:
        """
        Load ECB interest rate data

        Args:
            df: DataFrame with interest rate data

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No ECB rate data to load")
            return 0

        logger.info(f"Loading {len(df)} ECB rate records")

        rows_loaded = self.db.load_dataframe(
            df=df,
            table='raw_ecb_rates',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_ecb_rates")
        return rows_loaded

    def load_all_data(self, data_dict: Dict[str, Any]) -> Dict[str, int]:
        """
        Load all datasets from a dictionary

        Args:
            data_dict: Dictionary with keys mapping to datasets

        Returns:
            Dictionary with row counts for each dataset
        """
        logger.info("Starting bulk data load")

        results = {}

        # Load Daft listings
        if 'daft_listings' in data_dict:
            results['daft_listings'] = self.load_daft_listings(
                data_dict['daft_listings']
            )

        # Load CSO data
        if 'cso_rent_index' in data_dict:
            results['cso_rent_index'] = self.load_cso_rent_index(
                data_dict['cso_rent_index']
            )

        if 'cso_income' in data_dict:
            results['cso_income'] = self.load_cso_income(
                data_dict['cso_income']
            )

        # Load Property Sales
        if 'property_sales' in data_dict:
            results['property_sales'] = self.load_property_sales(
                data_dict['property_sales']
            )

        # Load ECB Rates
        if 'ecb_rates' in data_dict:
            results['ecb_rates'] = self.load_ecb_rates(
                data_dict['ecb_rates']
            )

        total_rows = sum(results.values())
        logger.info(f"Bulk load complete: {total_rows} total rows loaded")

        return results


def main():
    """Main function for testing the loader"""
    loader = DataLoader()
    logger.info("DataLoader initialized successfully")


if __name__ == "__main__":
    main()
