"""
Data Loader - Loads scraped data into PostgreSQL raw tables with complete field mapping
"""
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any

from etl.utils.database import db
from etl.utils.logger import get_logger

logger = get_logger(__name__)


class DataLoader:
    """Handles loading of raw data into PostgreSQL with complete schema support"""

    def __init__(self):
        self.db = db

    def load_daft_listings(self, listings: List[Dict]) -> int:
        """
        Load Daft.ie rental listings into raw_daft_listings table
        Maps all 38 fields from scraper output

        Args:
            listings: List of property listing dictionaries

        Returns:
            Number of rows inserted
        """
        if not listings:
            logger.warning("No Daft listings to load")
            return 0

        logger.info(f"Loading {len(listings)} Daft listings with complete field mapping")

        # Convert to DataFrame
        df = pd.DataFrame(listings)

        # Define all 38 expected fields
        required_columns = [
            'property_id', 'daft_shortcode', 'title', 'seo_title',
            'price', 'price_raw', 'abbreviated_price',
            'property_type', 'bedrooms', 'num_bedrooms_raw', 'county',
            'sections', 'sale_type', 'publish_date', 'date_of_construction',
            'category', 'state', 'featured_level', 'featured_level_full',
            'premier_partner', 'latitude', 'longitude', 'seo_friendly_path',
            'seller_id', 'seller_name', 'seller_phone', 'seller_branch',
            'seller_type', 'licence_number', 'total_images', 'has_video',
            'has_virtual_tour', 'has_brochure', 'ber_rating',
            'prs_total_unit_types', 'prs_tagline', 'property_url', 'scraped_at'
        ]

        # Add missing columns with None values
        for col in required_columns:
            if col not in df.columns:
                df[col] = None

        # Type conversions and cleaning
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['bedrooms'] = pd.to_numeric(df['bedrooms'], errors='coerce').astype('Int64')
        df['seller_id'] = pd.to_numeric(df['seller_id'], errors='coerce').astype('Int64')
        df['total_images'] = pd.to_numeric(df['total_images'], errors='coerce').astype('Int64')
        df['prs_total_unit_types'] = pd.to_numeric(df['prs_total_unit_types'], errors='coerce').astype('Int64')
        df['publish_date'] = pd.to_numeric(df['publish_date'], errors='coerce').astype('Int64')

        # Convert boolean fields
        df['premier_partner'] = df['premier_partner'].astype('boolean')
        df['has_video'] = df['has_video'].astype('boolean')
        df['has_virtual_tour'] = df['has_virtual_tour'].astype('boolean')
        df['has_brochure'] = df['has_brochure'].astype('boolean')

        # Ensure scraped_at is timestamp
        if 'scraped_at' in df.columns:
            df['scraped_at'] = pd.to_datetime(df['scraped_at'], errors='coerce')
        else:
            df['scraped_at'] = pd.Timestamp.now()

        # Select only the required columns in correct order
        df = df[required_columns]

        # Load to database
        rows_loaded = self.db.load_dataframe(
            df=df,
            table='raw_daft_listings',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} Daft listings with all 38 fields to raw_daft_listings")
        return rows_loaded

    def load_cso_rent(self, df: pd.DataFrame) -> int:
        """
        Load CSO Rent Index data (RIA02) with complete field mapping

        Args:
            df: DataFrame with rent index data from CSO API

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO rent index data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO rent index records")

        # Map CSV columns to database columns (handle BOM in first column)
        column_mapping = {
            '\ufeff"STATISTIC"': 'statistic_code',
            'STATISTIC': 'statistic_code',
            'STATISTIC Label': 'statistic_label',
            'TLIST(A1)': 'time_period',
            'Year': 'year',
            'C02970V03592': 'bedrooms_code',
            'Number of Bedrooms': 'bedrooms_label',
            'C02969V03591': 'property_type_code',
            'Property Type': 'property_type_label',
            'C03004V03625': 'location_code',
            'Location': 'location_label',
            'UNIT': 'unit',
            'VALUE': 'value'
        }

        # Find and map available columns
        df_renamed = df.rename(columns=column_mapping)

        # Add metadata if not present
        if 'date_fetched' not in df_renamed.columns:
            df_renamed['date_fetched'] = pd.Timestamp.now()
        if 'source' not in df_renamed.columns:
            df_renamed['source'] = 'cso.ie'

        # Type conversions
        if 'year' in df_renamed.columns:
            df_renamed['year'] = pd.to_numeric(df_renamed['year'], errors='coerce').astype('Int64')
        if 'value' in df_renamed.columns:
            df_renamed['value'] = pd.to_numeric(df_renamed['value'], errors='coerce')

        rows_loaded = self.db.load_dataframe(
            df=df_renamed,
            table='raw_cso_rent',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_cso_rent")
        return rows_loaded

    def load_cso_cpi(self, df: pd.DataFrame) -> int:
        """
        Load CSO Consumer Price Index data (CPA01)

        Args:
            df: DataFrame with CPI data from CSO API

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO CPI data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO CPI records")

        # Map CSV columns to database columns
        column_mapping = {
            '\ufeff"STATISTIC"': 'statistic_code',
            'STATISTIC': 'statistic_code',
            'Statistic Label': 'statistic_label',
            'TLIST(A1)': 'time_period',
            'Year': 'year',
            'C01779V03424': 'commodity_code',
            'Commodity Group': 'commodity_label',
            'UNIT': 'unit',
            'VALUE': 'value'
        }

        df_renamed = df.rename(columns=column_mapping)

        # Add metadata
        if 'date_fetched' not in df_renamed.columns:
            df_renamed['date_fetched'] = pd.Timestamp.now()
        if 'source' not in df_renamed.columns:
            df_renamed['source'] = 'cso.ie'

        # Type conversions
        if 'year' in df_renamed.columns:
            df_renamed['year'] = pd.to_numeric(df_renamed['year'], errors='coerce').astype('Int64')
        if 'value' in df_renamed.columns:
            df_renamed['value'] = pd.to_numeric(df_renamed['value'], errors='coerce')

        rows_loaded = self.db.load_dataframe(
            df=df_renamed,
            table='raw_cso_cpi',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_cso_cpi")
        return rows_loaded

    def load_cso_population(self, df: pd.DataFrame) -> int:
        """
        Load CSO Population data (PEA01)

        Args:
            df: DataFrame with population data from CSO API

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO population data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO population records")

        # Map CSV columns to database columns
        column_mapping = {
            '\ufeff"STATISTIC"': 'statistic_code',
            'STATISTIC': 'statistic_code',
            'STATISTIC Label': 'statistic_label',
            'TLIST(A1)': 'time_period',
            'Year': 'year',
            'C02076V02508': 'age_group_code',
            'Age Group': 'age_group_label',
            'C02199V02655': 'sex_code',
            'Sex': 'sex_label',
            'UNIT': 'unit',
            'VALUE': 'value'
        }

        df_renamed = df.rename(columns=column_mapping)

        # Add metadata
        if 'date_fetched' not in df_renamed.columns:
            df_renamed['date_fetched'] = pd.Timestamp.now()
        if 'source' not in df_renamed.columns:
            df_renamed['source'] = 'cso.ie'

        # Type conversions
        if 'year' in df_renamed.columns:
            df_renamed['year'] = pd.to_numeric(df_renamed['year'], errors='coerce').astype('Int64')
        if 'value' in df_renamed.columns:
            df_renamed['value'] = pd.to_numeric(df_renamed['value'], errors='coerce')

        rows_loaded = self.db.load_dataframe(
            df=df_renamed,
            table='raw_cso_population',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_cso_population")
        return rows_loaded

    def load_cso_income(self, df: pd.DataFrame) -> int:
        """
        Load CSO Disposable Income data (CIA01) - Updated with complete fields

        Args:
            df: DataFrame with income data from CSO API

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO income data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO income records")

        # Map CSV columns to database columns
        column_mapping = {
            '\ufeff"C02196V02652"': 'location_code',
            'C02196V02652': 'location_code',
            'County and Region': 'location_label',
            'TLIST(A1)': 'time_period',
            'Year': 'year',
            'STATISTIC': 'statistic_code',
            'Statistic Label': 'statistic_label',
            'UNIT': 'unit',
            'VALUE': 'value'
        }

        df_renamed = df.rename(columns=column_mapping)

        # Add metadata
        if 'date_fetched' not in df_renamed.columns:
            df_renamed['date_fetched'] = pd.Timestamp.now()
        if 'source' not in df_renamed.columns:
            df_renamed['source'] = 'cso.ie'

        # Type conversions
        if 'year' in df_renamed.columns:
            df_renamed['year'] = pd.to_numeric(df_renamed['year'], errors='coerce').astype('Int64')
        if 'value' in df_renamed.columns:
            df_renamed['value'] = pd.to_numeric(df_renamed['value'], errors='coerce')

        rows_loaded = self.db.load_dataframe(
            df=df_renamed,
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
        if 'cso_rent' in data_dict:
            results['cso_rent'] = self.load_cso_rent(
                data_dict['cso_rent']
            )

        if 'cso_income' in data_dict:
            results['cso_income'] = self.load_cso_income(
                data_dict['cso_income']
            )

        if 'cso_cpi' in data_dict:
            results['cso_cpi'] = self.load_cso_cpi(
                data_dict['cso_cpi']
            )

        if 'cso_population' in data_dict:
            results['cso_population'] = self.load_cso_population(
                data_dict['cso_population']
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
    logger.info("DataLoader initialized successfully with complete schema support")


if __name__ == "__main__":
    main()
