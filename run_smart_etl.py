#!/usr/bin/env python3
"""
Smart ETL Runner - Orchestrates Daft and CSO scrapers with automatic incremental loading
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from etl.scrapers.smart_daft_scraper import run_smart_scraper as run_daft
from etl.scrapers.smart_cso_scraper import run_smart_cso_scraper
from etl.utils.logger import get_logger

logger = get_logger(__name__)


def print_banner():
    """Print startup banner"""
    print("\n" + "="*70)
    print("🚀 IRELAND HOUSING DATA PLATFORM - SMART ETL")
    print("="*70)
    print("Features:")
    print("  ✅ Automatic Full/Incremental mode detection")
    print("  ✅ Daft.ie rental listings (all 38 fields)")
    print("  ✅ CSO official statistics (rent, CPI, population, income)")
    print("  ✅ Smart checkpoint tracking")
    print("="*70 + "\n")


async def run_full_pipeline(daft_only: bool = False, cso_only: bool = False, force_full: bool = False):
    """
    Run complete ETL pipeline with smart incremental loading

    Args:
        daft_only: Only run Daft scraper
        cso_only: Only run CSO scraper
        force_full: Force full load for all data sources
    """
    print_banner()

    results = {
        'daft': None,
        'cso': {}
    }

    # Run Daft scraper
    if not cso_only:
        logger.info("🏠 STEP 1: Daft.ie Rental Listings")
        logger.info("-" * 70)
        try:
            daft_success = await run_daft()
            results['daft'] = daft_success
        except Exception as e:
            logger.error(f"Daft scraper failed: {e}")
            results['daft'] = False

        print()  # Spacing

    # Run CSO scrapers
    if not daft_only:
        logger.info("📊 STEP 2: CSO Official Statistics")
        logger.info("-" * 70)
        try:
            cso_results = run_smart_cso_scraper(force_full=force_full)
            results['cso'] = cso_results
        except Exception as e:
            logger.error(f"CSO scraper failed: {e}")

    # Final summary
    print("\n" + "="*70)
    print("📈 ETL PIPELINE SUMMARY")
    print("="*70)

    if results['daft'] is not None:
        status = "✅ SUCCESS" if results['daft'] else "❌ FAILED"
        print(f"{status}: Daft.ie Scraper")

    if results['cso']:
        for dataset, success in results['cso'].items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{status}: CSO {dataset.upper()}")

    print("="*70)
    print("\n💡 Next steps:")
    print("   1. Run dbt models: cd dbt && dbt run --profiles-dir .")
    print("   2. Run tests: cd dbt && dbt test --profiles-dir .")
    print("   3. Query data: SELECT * FROM marts.fact_listings;")
    print("="*70 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Smart ETL Pipeline for Ireland Housing Data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline (automatic mode detection)
  python run_smart_etl.py

  # Force full refresh of all data
  python run_smart_etl.py --force-full

  # Only run Daft scraper
  python run_smart_etl.py --daft-only

  # Only run CSO scrapers
  python run_smart_etl.py --cso-only
        """
    )

    parser.add_argument(
        '--daft-only',
        action='store_true',
        help='Only run Daft.ie scraper'
    )

    parser.add_argument(
        '--cso-only',
        action='store_true',
        help='Only run CSO scrapers'
    )

    parser.add_argument(
        '--force-full',
        action='store_true',
        help='Force full load (ignore existing data)'
    )

    args = parser.parse_args()

    # Run pipeline
    asyncio.run(run_full_pipeline(
        daft_only=args.daft_only,
        cso_only=args.cso_only,
        force_full=args.force_full
    ))


if __name__ == "__main__":
    main()
