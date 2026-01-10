"""
Central Statistics Office (CSO) API Client
Fetches Irish statistical data on rents, income, population, and CPI
"""
import requests
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

from etl.config import Config
from etl.utils.logger import get_logger

logger = get_logger(__name__)


class CSOScraper:
    """Client for CSO Ireland Open Data API"""

    def __init__(self):
        self.base_url = Config.CSO_API_BASE
        self.headers = {
            'User-Agent': Config.USER_AGENT,
            'Accept': 'application/json'
        }

    def fetch_rent_index(self) -> pd.DataFrame:
        """
        Fetch Residential Tenancies Rent Index
        Dataset: RTI - Residential Tenancies Index

        Returns:
            DataFrame with rent index data by county and time period
        """
        logger.info("Fetching CSO Rent Index data")

        # Note: Update this URL with actual CSO dataset ID
        # Example: https://data.cso.ie/api/dataset/RTI01
        url = f"{self.base_url}/api/dataset/RTI01"

        try:
            response = requests.get(url, headers=self.headers, timeout=Config.TIMEOUT_SECONDS)
            response.raise_for_status()

            data = response.json()
            df = self._parse_cso_json(data)

            logger.info(f"Fetched {len(df)} rent index records")
            return df

        except requests.RequestException as e:
            logger.error(f"Error fetching rent index: {e}")
            return pd.DataFrame()

    def fetch_disposable_income(self) -> pd.DataFrame:
        """
        Fetch Disposable Income data by county

        Returns:
            DataFrame with disposable income by county and year
        """
        logger.info("Fetching CSO Disposable Income data")

        # Note: Update with actual CSO dataset ID
        url = f"{self.base_url}/api/dataset/CIA01"

        try:
            response = requests.get(url, headers=self.headers, timeout=Config.TIMEOUT_SECONDS)
            response.raise_for_status()

            data = response.json()
            df = self._parse_cso_json(data)

            logger.info(f"Fetched {len(df)} disposable income records")
            return df

        except requests.RequestException as e:
            logger.error(f"Error fetching disposable income: {e}")
            return pd.DataFrame()

    def fetch_population_data(self) -> pd.DataFrame:
        """
        Fetch Population data by county

        Returns:
            DataFrame with population by county
        """
        logger.info("Fetching CSO Population data")

        # Note: Update with actual CSO dataset ID
        url = f"{self.base_url}/api/dataset/PEA01"

        try:
            response = requests.get(url, headers=self.headers, timeout=Config.TIMEOUT_SECONDS)
            response.raise_for_status()

            data = response.json()
            df = self._parse_cso_json(data)

            logger.info(f"Fetched {len(df)} population records")
            return df

        except requests.RequestException as e:
            logger.error(f"Error fetching population data: {e}")
            return pd.DataFrame()

    def fetch_cpi_data(self) -> pd.DataFrame:
        """
        Fetch Consumer Price Index (CPI) data

        Returns:
            DataFrame with CPI data over time
        """
        logger.info("Fetching CSO CPI data")

        # Note: Update with actual CSO dataset ID
        url = f"{self.base_url}/api/dataset/CPM01"

        try:
            response = requests.get(url, headers=self.headers, timeout=Config.TIMEOUT_SECONDS)
            response.raise_for_status()

            data = response.json()
            df = self._parse_cso_json(data)

            logger.info(f"Fetched {len(df)} CPI records")
            return df

        except requests.RequestException as e:
            logger.error(f"Error fetching CPI data: {e}")
            return pd.DataFrame()

    def _parse_cso_json(self, data: Dict) -> pd.DataFrame:
        """
        Parse CSO JSON response into DataFrame

        Args:
            data: JSON response from CSO API

        Returns:
            Parsed DataFrame
        """
        # CSO API structure varies by dataset
        # This is a generic parser - adjust based on actual API response
        try:
            if 'value' in data:
                df = pd.DataFrame(data['value'])
            elif 'data' in data:
                df = pd.DataFrame(data['data'])
            else:
                df = pd.DataFrame(data)

            # Add metadata
            df['date_fetched'] = datetime.now()
            df['source'] = 'cso.ie'

            return df

        except Exception as e:
            logger.error(f"Error parsing CSO JSON: {e}")
            return pd.DataFrame()

    def fetch_all_datasets(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch all CSO datasets

        Returns:
            Dictionary of DataFrames keyed by dataset name
        """
        logger.info("Fetching all CSO datasets")

        datasets = {
            'rent_index': self.fetch_rent_index(),
            'disposable_income': self.fetch_disposable_income(),
            'population': self.fetch_population_data(),
            'cpi': self.fetch_cpi_data()
        }

        total_records = sum(len(df) for df in datasets.values())
        logger.info(f"Fetched {total_records} total CSO records across {len(datasets)} datasets")

        return datasets


def main():
    """Main function to run the CSO scraper"""
    scraper = CSOScraper()
    datasets = scraper.fetch_all_datasets()

    for name, df in datasets.items():
        logger.info(f"{name}: {len(df)} records")

    return datasets


if __name__ == "__main__":
    main()
