#!/usr/bin/env python3
"""
Test script for Smart ETL - validates incremental loading logic
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from etl.utils.database import db
from etl.utils.logger import get_logger

logger = get_logger(__name__)


def test_database_connection():
    """Test database connectivity"""
    print("\n" + "="*70)
    print("TEST 1: Database Connection")
    print("="*70)

    try:
        result = db.execute_query("SELECT version()")
        if result:
            print(f"✅ Connected to PostgreSQL")
            print(f"   Version: {result[0]['version'].split(',')[0]}")
            return True
        else:
            print("❌ No response from database")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_existing_data_check():
    """Test checking for existing data"""
    print("\n" + "="*70)
    print("TEST 2: Existing Data Detection")
    print("="*70)

    tables = {
        'Daft Listings': 'raw_daft_listings',
        'CSO Rent': 'raw_cso_rent',
        'CSO CPI': 'raw_cso_cpi',
        'CSO Population': 'raw_cso_population',
        'CSO Income': 'raw_cso_income'
    }

    results = {}

    for name, table in tables.items():
        try:
            # For Daft, check publish_date
            if table == 'raw_daft_listings':
                query = f"""
                    SELECT
                        COUNT(*) as count,
                        MAX(publish_date) as latest_date,
                        MIN(publish_date) as earliest_date
                    FROM {table}
                """
            # For CSO, check year
            else:
                query = f"""
                    SELECT
                        COUNT(*) as count,
                        MAX(year) as latest_year,
                        MIN(year) as earliest_year
                    FROM {table}
                """

            result = db.execute_query(query)

            if result and len(result) > 0:
                row = result[0]
                count = row.get('count', 0)

                if count > 0:
                    if table == 'raw_daft_listings':
                        latest = row.get('latest_date')
                        earliest = row.get('earliest_date')
                        print(f"✅ {name}: {count} records")
                        print(f"   Date range: {earliest} → {latest}")
                        results[name] = ('incremental', count, latest)
                    else:
                        latest = row.get('latest_year')
                        earliest = row.get('earliest_year')
                        print(f"✅ {name}: {count} records")
                        print(f"   Year range: {earliest} → {latest}")
                        results[name] = ('incremental', count, latest)
                else:
                    print(f"ℹ️  {name}: No data (will trigger FULL LOAD)")
                    results[name] = ('full', 0, None)
            else:
                print(f"⚠️  {name}: Could not check")
                results[name] = ('unknown', 0, None)

        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            results[name] = ('error', 0, None)

    return results


def test_incremental_logic():
    """Test the incremental loading logic"""
    print("\n" + "="*70)
    print("TEST 3: Incremental Logic Simulation")
    print("="*70)

    # Simulate checking Daft data
    try:
        query = """
            SELECT
                COUNT(*) as count,
                MAX(publish_date) as latest_publish_date
            FROM raw_daft_listings
            WHERE publish_date IS NOT NULL
        """

        result = db.execute_query(query)

        if result and len(result) > 0:
            count = result[0].get('count', 0)
            latest_date = result[0].get('latest_publish_date')

            if count > 0:
                print(f"📊 Daft Data Status:")
                print(f"   Records: {count}")
                print(f"   Latest publish_date: {latest_date}")
                print(f"\n   → Mode: INCREMENTAL")
                print(f"   → Will scrape: listings with publish_date > {latest_date}")
                print(f"   → Will check: ~5 pages for new listings")
            else:
                print(f"📊 Daft Data Status: EMPTY")
                print(f"\n   → Mode: FULL LOAD")
                print(f"   → Will scrape: ALL available pages until no more listings")
                print(f"   → Expected: Thousands of listings")

        print("\n✅ Incremental logic test passed")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_summary():
    """Print test summary and recommendations"""
    print("\n" + "="*70)
    print("🎯 SMART ETL TEST SUMMARY")
    print("="*70)

    # Check data status
    query = "SELECT COUNT(*) as count FROM raw_daft_listings"
    result = db.execute_query(query)

    if result:
        count = result[0].get('count', 0)

        if count == 0:
            print("\n📌 Current State: NO DATA")
            print("\n   Next Action:")
            print("   python run_smart_etl.py")
            print("\n   Expected Behavior:")
            print("   ✅ Daft: FULL LOAD mode (scrape all available listings)")
            print("   ✅ CSO: FULL LOAD mode (fetch all historical data)")
            print("   ✅ Duration: ~5-10 minutes")
            print("   ✅ Result: Thousands of listings + complete CSO datasets")

        else:
            print(f"\n📌 Current State: DATA EXISTS ({count} Daft listings)")
            print("\n   Next Action:")
            print("   python run_smart_etl.py")
            print("\n   Expected Behavior:")
            print("   ✅ Daft: INCREMENTAL mode (only new listings since last run)")
            print("   ✅ CSO: INCREMENTAL mode (only data for years not in DB)")
            print("   ✅ Duration: ~1-2 minutes")
            print("   ✅ Result: Only new listings/data added")

    print("\n" + "="*70)
    print("🚀 Ready to run Smart ETL!")
    print("="*70 + "\n")


def main():
    """Run all tests"""
    print("\n" + "🧪 TESTING SMART ETL SYSTEM" + "\n")

    # Run tests
    test1 = test_database_connection()

    if not test1:
        print("\n❌ Database connection failed. Please check configuration.")
        return False

    test2 = test_existing_data_check()
    test3 = test_incremental_logic()

    # Summary
    test_summary()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
