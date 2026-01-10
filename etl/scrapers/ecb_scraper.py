"""
European Central Bank (ECB) Interest Rates Scraper
Fetches ECB interest rate data for mortgage pressure analysis
"""
import requests
from datetime import datetime
import pandas as pd
from typing import Dict, Optional

from etl.config import Config
from etl.utils.logger import get_logger

logger = get_logger(__name__)


class ECBScraper:
    """Client for ECB Statistical Data Warehouse API"""

    def __init__(self):
        self.base_url = Config.ECB_API_BASE
        self.headers = {
            'User-Agent': Config.USER_AGENT,
            'Accept': 'application/json'
        }

    def fetch_interest_rates(self) -> pd.DataFrame:
        """
        Fetch ECB interest rate data

        Uses ECB's SDW API to get:
        - Main refinancing operations rate
        - Deposit facility rate
        - Marginal lending facility rate

        Returns:
            DataFrame with interest rate data
        """
        logger.info("Fetching ECB interest rates")

        # ECB Data Flow: FM (Financial Markets)
        # Series key for main policy rates
        # Example URL structure (update as needed):
        # https://sdw-wsrest.ecb.europa.eu/service/data/FM/M.U2.EUR.4F.KR.MRR_FR.LEV

        rates_to_fetch = {
            'main_refinancing': 'FM/M.U2.EUR.4F.KR.MRR_FR.LEV',
            'deposit_facility': 'FM/M.U2.EUR.4F.KR.DFR.LEV',
            'marginal_lending': 'FM/M.U2.EUR.4F.KR.MLFR.LEV'
        }

        all_rates = []

        for rate_name, series_key in rates_to_fetch.items():
            try:
                df = self._fetch_series(series_key, rate_name)
                all_rates.append(df)
            except Exception as e:
                logger.error(f"Error fetching {rate_name}: {e}")
                continue

        if all_rates:
            combined_df = pd.concat(all_rates, ignore_index=True)
            logger.info(f"Fetched {len(combined_df)} interest rate records")
            return combined_df
        else:
            logger.warning("No interest rate data fetched")
            return pd.DataFrame()

    def _fetch_series(self, series_key: str, rate_name: str) -> pd.DataFrame:
        """
        Fetch a specific data series from ECB

        Args:
            series_key: ECB series identifier
            rate_name: Human-readable rate name

        Returns:
            DataFrame with rate data
        """
        # ECB REST API endpoint
        url = f"{self.base_url}/service/data/{series_key}"

        params = {
            'format': 'jsondata',
            'detail': 'dataonly'
        }

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=Config.TIMEOUT_SECONDS
            )
            response.raise_for_status()

            data = response.json()
            df = self._parse_ecb_json(data, rate_name)

            logger.info(f"Fetched {len(df)} records for {rate_name}")
            return df

        except requests.RequestException as e:
            logger.error(f"HTTP error fetching {rate_name}: {e}")
            raise

    def _parse_ecb_json(self, data: Dict, rate_name: str) -> pd.DataFrame:
        """
        Parse ECB JSON response

        Args:
            data: JSON response from ECB API
            rate_name: Name of the rate

        Returns:
            Parsed DataFrame
        """
        try:
            # ECB JSON structure: data.dataSets[0].series
            observations = data.get('dataSets', [{}])[0].get('series', {})

            records = []
            for series_key, series_data in observations.items():
                obs_data = series_data.get('observations', {})

                for time_period, values in obs_data.items():
                    records.append({
                        'rate_type': rate_name,
                        'time_period': time_period,
                        'rate_value': values[0] if values else None,
                        'series_key': series_key
                    })

            df = pd.DataFrame(records)

            # Add metadata
            df['date_fetched'] = datetime.now()
            df['source'] = 'ecb.europa.eu'

            return df

        except Exception as e:
            logger.error(f"Error parsing ECB JSON for {rate_name}: {e}")
            return pd.DataFrame()

    def fetch_mortgage_rates(self) -> pd.DataFrame:
        """
        Fetch retail mortgage interest rates for Ireland

        Returns:
            DataFrame with mortgage rate data
        """
        logger.info("Fetching ECB mortgage rates for Ireland")

        # MIR (Monetary and Financial Institution Interest Rates)
        # Series for Ireland mortgage rates
        series_key = 'MIR/M.IE.B.A2C.AM.R.A.2250.EUR.N'

        try:
            df = self._fetch_series(series_key, 'ireland_mortgage_rate')
            return df
        except Exception as e:
            logger.error(f"Error fetching mortgage rates: {e}")
            return pd.DataFrame()


def main():
    """Main function to run the ECB scraper"""
    scraper = ECBScraper()

    # Fetch policy rates
    policy_rates = scraper.fetch_interest_rates()
    logger.info(f"Policy rates: {len(policy_rates)} records")

    # Fetch mortgage rates
    mortgage_rates = scraper.fetch_mortgage_rates()
    logger.info(f"Mortgage rates: {len(mortgage_rates)} records")

    return {
        'policy_rates': policy_rates,
        'mortgage_rates': mortgage_rates
    }


if __name__ == "__main__":
    main()
