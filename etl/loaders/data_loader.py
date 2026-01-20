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
        Deduplicates based on property_id + publish_date

        Args:
            listings: List of property listing dictionaries

        Returns:
            Number of rows inserted (excluding duplicates)
        """
        if not listings:
            logger.warning("No Daft listings to load")
            return 0

        logger.info(f"Loading {len(listings)} Daft listings with complete field mapping")

        # Convert to DataFrame
        df = pd.DataFrame(listings)

        # Remove duplicates within the batch itself
        original_count = len(df)
        df = df.drop_duplicates(subset=['property_id', 'publish_date'], keep='first')
        batch_dupes = original_count - len(df)
        if batch_dupes > 0:
            logger.info(f"Removed {batch_dupes} duplicates within batch")

        # Convert publish_date to numeric BEFORE duplicate check (DB stores as bigint)
        if 'publish_date' in df.columns:
            df['publish_date'] = pd.to_numeric(df['publish_date'], errors='coerce').astype('Int64')

        # Check for existing records in database to avoid duplicates
        if len(df) > 0:
            # Filter to rows with valid property_id and publish_date before querying
            valid_df = df[df['property_id'].notna() & df['publish_date'].notna()]

            if len(valid_df) > 0:
                property_ids = valid_df['property_id'].tolist()
                publish_dates = valid_df['publish_date'].tolist()

                # Build query to check existing combinations
                # property_id is VARCHAR (needs quotes), publish_date is bigint (no quotes)
                placeholders = ','.join([f"('{pid}',{pd})" for pid, pd in zip(property_ids, publish_dates)])

                if placeholders:
                    check_query = f"""
                        SELECT property_id, publish_date
                        FROM raw_daft_listings
                        WHERE (property_id, publish_date) IN ({placeholders})
                    """

                    try:
                        existing = self.db.execute_query(check_query)
                        if existing:
                            existing_set = {(row['property_id'], row['publish_date']) for row in existing}

                            # Filter out existing records
                            df = df[~df.apply(lambda row: (row['property_id'], row['publish_date']) in existing_set, axis=1)]

                            db_dupes = len(existing)
                            logger.info(f"Filtered out {db_dupes} records that already exist in database")
                    except Exception as e:
                        logger.warning(f"Could not check for existing records: {e}. Proceeding with all records.")

        if len(df) == 0:
            logger.info("No new records to load after deduplication")
            return 0

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
        # publish_date already converted earlier (before duplicate check)

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
        Load CSO Rent Index data (RIA02) with complete field mapping and deduplication

        Args:
            df: DataFrame with rent index data from CSO API

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO rent index data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO rent index records")

        # Map CSV/JSON-stat columns to database columns
        column_mapping = {
            '\ufeff"STATISTIC"': 'statistic_code',
            'STATISTIC': 'statistic_code',
            'STATISTIC Label': 'statistic_label',
            'STATISTIC_Label': 'statistic_label',  # JSON-stat format
            'TLIST(A1)': 'time_period',
            'Year': 'year',
            'C02970V03592': 'bedrooms_code',
            'C02970V03592_Label': 'bedrooms_label',  # JSON-stat format
            'Number of Bedrooms': 'bedrooms_label',
            'C02969V03591': 'property_type_code',
            'C02969V03591_Label': 'property_type_label',  # JSON-stat format
            'Property Type': 'property_type_label',
            'C03004V03625': 'location_code',
            'C03004V03625_Label': 'location_label',  # JSON-stat format
            'Location': 'location_label',
            'UNIT': 'unit',
            'VALUE': 'value'
        }

        # Find and map available columns
        df_renamed = df.rename(columns=column_mapping)

        # Drop any extra Label columns we don't need
        cols_to_drop = [col for col in df_renamed.columns if col.endswith('_Label') and col not in column_mapping.values()]
        if cols_to_drop:
            df_renamed = df_renamed.drop(columns=cols_to_drop)

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

        # Deduplication: Remove records that already exist in database
        original_count = len(df_renamed)
        if original_count > 0 and 'year' in df_renamed.columns:
            # Check for existing records based on unique combination of year, location, bedrooms, property_type
            dedup_cols = ['year', 'location_label', 'bedrooms_label', 'property_type_label']
            valid_cols = [col for col in dedup_cols if col in df_renamed.columns]

            if len(valid_cols) >= 2:  # Need at least year and one other dimension
                try:
                    # Get unique years to check
                    years = df_renamed['year'].dropna().unique().tolist()
                    if years:
                        year_list = ','.join([str(int(y)) for y in years])
                        check_query = f"""
                            SELECT DISTINCT {', '.join(valid_cols)}
                            FROM raw_cso_rent
                            WHERE year IN ({year_list})
                        """

                        existing = self.db.execute_query(check_query)
                        if existing:
                            # Create set of existing combinations
                            existing_set = {tuple(row[col] for col in valid_cols) for row in existing}

                            # Filter out existing records
                            df_renamed = df_renamed[~df_renamed.apply(
                                lambda row: tuple(row[col] for col in valid_cols) in existing_set, axis=1
                            )]

                            deduped = original_count - len(df_renamed)
                            if deduped > 0:
                                logger.info(f"Filtered out {deduped} records that already exist in database")
                except Exception as e:
                    logger.warning(f"Could not check for existing records: {e}. Proceeding with all records.")

        if len(df_renamed) == 0:
            logger.info("No new records to load after deduplication")
            return 0

        rows_loaded = self.db.load_dataframe(
            df=df_renamed,
            table='raw_cso_rent',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_cso_rent")
        return rows_loaded

    def load_cso_cpi(self, df: pd.DataFrame) -> int:
        """
        Load CSO Consumer Price Index data (CPA01) with deduplication

        Args:
            df: DataFrame with CPI data from CSO API

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO CPI data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO CPI records")

        # Map CSV/JSON-stat columns to database columns
        column_mapping = {
            '\ufeff"STATISTIC"': 'statistic_code',
            'STATISTIC': 'statistic_code',
            'Statistic Label': 'statistic_label',
            'STATISTIC_Label': 'statistic_label',  # JSON-stat format
            'TLIST(A1)': 'time_period',
            'TLIST(M1)': 'time_period',  # Monthly time periods
            'TLIST(Q1)': 'time_period',  # Quarterly time periods
            'Year': 'year',
            'C01779V03424': 'commodity_code',
            'C01779V03424_Label': 'commodity_label',  # JSON-stat format
            'Commodity Group': 'commodity_label',
            'UNIT': 'unit',
            'VALUE': 'value'
        }

        df_renamed = df.rename(columns=column_mapping)

        # Drop any extra Label columns we don't need
        cols_to_drop = [col for col in df_renamed.columns if col.endswith('_Label') and col not in column_mapping.values()]
        if cols_to_drop:
            df_renamed = df_renamed.drop(columns=cols_to_drop)

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

        # Deduplication: Remove records that already exist in database
        original_count = len(df_renamed)
        if original_count > 0 and 'year' in df_renamed.columns:
            dedup_cols = ['year', 'commodity_label', 'statistic_code']
            valid_cols = [col for col in dedup_cols if col in df_renamed.columns]

            if len(valid_cols) >= 2:
                try:
                    years = df_renamed['year'].dropna().unique().tolist()
                    if years:
                        year_list = ','.join([str(int(y)) for y in years])
                        check_query = f"""
                            SELECT DISTINCT {', '.join(valid_cols)}
                            FROM raw_cso_cpi
                            WHERE year IN ({year_list})
                        """

                        existing = self.db.execute_query(check_query)
                        if existing:
                            existing_set = {tuple(row[col] for col in valid_cols) for row in existing}
                            df_renamed = df_renamed[~df_renamed.apply(
                                lambda row: tuple(row[col] for col in valid_cols) in existing_set, axis=1
                            )]

                            deduped = original_count - len(df_renamed)
                            if deduped > 0:
                                logger.info(f"Filtered out {deduped} records that already exist in database")
                except Exception as e:
                    logger.warning(f"Could not check for existing records: {e}. Proceeding with all records.")

        if len(df_renamed) == 0:
            logger.info("No new records to load after deduplication")
            return 0

        rows_loaded = self.db.load_dataframe(
            df=df_renamed,
            table='raw_cso_cpi',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_cso_cpi")
        return rows_loaded

    def load_cso_population(self, df: pd.DataFrame) -> int:
        """
        Load CSO Population data (PEA01) with deduplication

        Args:
            df: DataFrame with population data from CSO API

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO population data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO population records")

        # Map CSV/JSON-stat columns to database columns
        column_mapping = {
            '\ufeff"STATISTIC"': 'statistic_code',
            'STATISTIC': 'statistic_code',
            'STATISTIC Label': 'statistic_label',
            'STATISTIC_Label': 'statistic_label',  # JSON-stat format
            'TLIST(A1)': 'time_period',
            'Year': 'year',
            'C02076V02508': 'age_group_code',
            'C02076V02508_Label': 'age_group_label',  # JSON-stat format
            'Age Group': 'age_group_label',
            'C02199V02655': 'sex_code',
            'C02199V02655_Label': 'sex_label',  # JSON-stat format
            'Sex': 'sex_label',
            'UNIT': 'unit',
            'VALUE': 'value'
        }

        df_renamed = df.rename(columns=column_mapping)

        # Drop any extra Label columns we don't need
        cols_to_drop = [col for col in df_renamed.columns if col.endswith('_Label') and col not in column_mapping.values()]
        if cols_to_drop:
            df_renamed = df_renamed.drop(columns=cols_to_drop)

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

        # Deduplication: Remove records that already exist in database
        original_count = len(df_renamed)
        if original_count > 0 and 'year' in df_renamed.columns:
            dedup_cols = ['year', 'age_group_label', 'sex_label']
            valid_cols = [col for col in dedup_cols if col in df_renamed.columns]

            if len(valid_cols) >= 2:
                try:
                    years = df_renamed['year'].dropna().unique().tolist()
                    if years:
                        year_list = ','.join([str(int(y)) for y in years])
                        check_query = f"""
                            SELECT DISTINCT {', '.join(valid_cols)}
                            FROM raw_cso_population
                            WHERE year IN ({year_list})
                        """

                        existing = self.db.execute_query(check_query)
                        if existing:
                            existing_set = {tuple(row[col] for col in valid_cols) for row in existing}
                            df_renamed = df_renamed[~df_renamed.apply(
                                lambda row: tuple(row[col] for col in valid_cols) in existing_set, axis=1
                            )]

                            deduped = original_count - len(df_renamed)
                            if deduped > 0:
                                logger.info(f"Filtered out {deduped} records that already exist in database")
                except Exception as e:
                    logger.warning(f"Could not check for existing records: {e}. Proceeding with all records.")

        if len(df_renamed) == 0:
            logger.info("No new records to load after deduplication")
            return 0

        rows_loaded = self.db.load_dataframe(
            df=df_renamed,
            table='raw_cso_population',
            if_exists='append'
        )

        logger.info(f"Loaded {rows_loaded} records to raw_cso_population")
        return rows_loaded

    def load_cso_income(self, df: pd.DataFrame) -> int:
        """
        Load CSO Disposable Income data (CIA01) with deduplication

        Args:
            df: DataFrame with income data from CSO API

        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("No CSO income data to load")
            return 0

        logger.info(f"Loading {len(df)} CSO income records")

        # Map CSV/JSON-stat columns to database columns
        column_mapping = {
            '\ufeff"C02196V02652"': 'location_code',
            'C02196V02652': 'location_code',
            'C02196V02652_Label': 'location_label',  # JSON-stat format
            'County and Region': 'location_label',
            'TLIST(A1)': 'time_period',
            'Year': 'year',
            'STATISTIC': 'statistic_code',
            'Statistic Label': 'statistic_label',
            'STATISTIC_Label': 'statistic_label',  # JSON-stat format
            'UNIT': 'unit',
            'VALUE': 'value'
        }

        df_renamed = df.rename(columns=column_mapping)

        # Drop any extra Label columns we don't need
        cols_to_drop = [col for col in df_renamed.columns if col.endswith('_Label') and col not in column_mapping.values()]
        if cols_to_drop:
            df_renamed = df_renamed.drop(columns=cols_to_drop)

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

        # Deduplication: Remove records that already exist in database
        original_count = len(df_renamed)
        if original_count > 0 and 'year' in df_renamed.columns:
            dedup_cols = ['year', 'location_label', 'statistic_code']
            valid_cols = [col for col in dedup_cols if col in df_renamed.columns]

            if len(valid_cols) >= 2:
                try:
                    years = df_renamed['year'].dropna().unique().tolist()
                    if years:
                        year_list = ','.join([str(int(y)) for y in years])
                        check_query = f"""
                            SELECT DISTINCT {', '.join(valid_cols)}
                            FROM raw_cso_income
                            WHERE year IN ({year_list})
                        """

                        existing = self.db.execute_query(check_query)
                        if existing:
                            existing_set = {tuple(row[col] for col in valid_cols) for row in existing}
                            df_renamed = df_renamed[~df_renamed.apply(
                                lambda row: tuple(row[col] for col in valid_cols) in existing_set, axis=1
                            )]

                            deduped = original_count - len(df_renamed)
                            if deduped > 0:
                                logger.info(f"Filtered out {deduped} records that already exist in database")
                except Exception as e:
                    logger.warning(f"Could not check for existing records: {e}. Proceeding with all records.")

        if len(df_renamed) == 0:
            logger.info("No new records to load after deduplication")
            return 0

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
