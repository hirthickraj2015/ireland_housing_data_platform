"""
Property Price Register Scraper
Fetches property sale prices from the Irish Property Price Register
"""
import requests
from datetime import datetime
import pandas as pd
from typing import Optional
import io

from etl.config import Config
from etl.utils.logger import get_logger

logger = get_logger(__name__)


class PropertyPriceScraper:
    """Scraper for Irish Property Price Register"""

    def __init__(self):
        self.base_url = Config.PROPERTY_REGISTER_URL
        self.headers = {
            'User-Agent': Config.USER_AGENT
        }

    def fetch_property_prices(self, year: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch property price data

        The Property Price Register provides CSV downloads of all property sales

        Args:
            year: Optional year to filter (defaults to current year)

        Returns:
            DataFrame with property sale data
        """
        if not year:
            year = datetime.now().year

        logger.info(f"Fetching property prices for year {year}")

        # Note: The actual download URL may vary
        # Check https://www.propertypriceregister.ie/ for current download links
        # Example URL format (adjust as needed):
        csv_url = f"{self.base_url}/website/npsra/pprweb.nsf/Downloads/PPR-ALL.csv/$FILE/PPR-ALL.csv"

        try:
            response = requests.get(
                csv_url,
                headers=self.headers,
                timeout=60  # Larger timeout for big CSV files
            )
            response.raise_for_status()

            # Parse CSV
            df = pd.read_csv(
                io.StringIO(response.text),
                encoding='latin-1'
            )

            # Standardize column names
            df.columns = df.columns.str.lower().str.replace(' ', '_')

            # Add metadata
            df['date_fetched'] = datetime.now()
            df['source'] = 'propertypriceregister.ie'

            # Filter by year if specified
            if 'date_of_sale' in df.columns:
                df['date_of_sale'] = pd.to_datetime(df['date_of_sale'])
                df = df[df['date_of_sale'].dt.year == year]

            logger.info(f"Fetched {len(df)} property sale records for {year}")
            return df

        except requests.RequestException as e:
            logger.error(f"Error fetching property prices: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error parsing property price data: {e}")
            return pd.DataFrame()

    def fetch_recent_sales(self, months: int = 12) -> pd.DataFrame:
        """
        Fetch property sales from the last N months

        Args:
            months: Number of months to look back

        Returns:
            DataFrame with recent property sales
        """
        logger.info(f"Fetching property sales from last {months} months")

        # Fetch current year and previous year to ensure coverage
        current_year = datetime.now().year
        df_current = self.fetch_property_prices(year=current_year)
        df_previous = self.fetch_property_prices(year=current_year - 1)

        # Combine and filter by date
        df_combined = pd.concat([df_current, df_previous], ignore_index=True)

        if 'date_of_sale' in df_combined.columns:
            cutoff_date = pd.Timestamp.now() - pd.DateOffset(months=months)
            df_filtered = df_combined[df_combined['date_of_sale'] >= cutoff_date]

            logger.info(f"Filtered to {len(df_filtered)} sales in last {months} months")
            return df_filtered

        return df_combined

    def aggregate_by_county(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate property prices by county

        Args:
            df: DataFrame with property sale data

        Returns:
            Aggregated DataFrame with average prices by county
        """
        if df.empty or 'county' not in df.columns or 'price' not in df.columns:
            logger.warning("Cannot aggregate: missing required columns")
            return pd.DataFrame()

        aggregated = df.groupby('county').agg({
            'price': ['mean', 'median', 'count'],
            'date_of_sale': ['min', 'max']
        }).reset_index()

        # Flatten column names
        aggregated.columns = [
            'county', 'avg_price', 'median_price', 'num_sales',
            'earliest_sale', 'latest_sale'
        ]

        logger.info(f"Aggregated data for {len(aggregated)} counties")
        return aggregated


def main():
    """Main function to run the property price scraper"""
    scraper = PropertyPriceScraper()

    # Fetch recent sales
    df = scraper.fetch_recent_sales(months=12)
    logger.info(f"Fetched {len(df)} recent property sales")

    # Aggregate by county
    if not df.empty:
        county_stats = scraper.aggregate_by_county(df)
        logger.info(f"County aggregation complete: {len(county_stats)} counties")

    return df


if __name__ == "__main__":
    main()
