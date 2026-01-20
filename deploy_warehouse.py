#!/usr/bin/env python3
"""
Deploy Data Warehouse - Ireland Housing Platform
Builds complete medallion architecture: Bronze → Silver → Gold
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration from environment
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'neondb'),
    'user': os.getenv('DB_USER', 'neondb_owner'),
    'password': os.getenv('DB_PASSWORD', 'npg_e3y6gIFNHsaD')
}

# SQL scripts to execute in order
SQL_SCRIPTS = [
    'sql/01_create_silver_layer.sql',
    'sql/02_create_gold_dimensions.sql',
    'sql/03_create_gold_facts.sql'
]


def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)


def execute_sql_file(conn, file_path):
    """Execute a SQL file"""
    script_name = os.path.basename(file_path)

    try:
        # Read SQL file
        with open(file_path, 'r') as f:
            sql_content = f.read()

        logger.info(f"📄 Executing: {script_name}")
        logger.info("=" * 70)

        # Create cursor with server-side messages
        cur = conn.cursor()

        # Execute SQL
        cur.execute(sql_content)
        conn.commit()

        # Get notices (RAISE NOTICE output)
        for notice in conn.notices:
            print(notice.strip())

        conn.notices.clear()

        logger.info(f"✅ SUCCESS: {script_name}")
        logger.info("")

        cur.close()
        return True

    except Exception as e:
        logger.error(f"❌ FAILED: {script_name}")
        logger.error(f"Error: {str(e)}")
        conn.rollback()
        return False


def check_prerequisites(conn):
    """Check if raw data exists"""
    logger.info("🔍 Checking prerequisites...")
    logger.info("=" * 70)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Check if raw tables exist and have data
    tables_to_check = [
        ('raw_daft_listings', 'Daft Listings'),
        ('raw_cso_rent', 'CSO Rent Index'),
        ('raw_cso_cpi', 'CSO CPI'),
        ('raw_cso_population', 'CSO Population'),
        ('raw_cso_income', 'CSO Income')
    ]

    all_good = True
    total_records = 0

    for table_name, display_name in tables_to_check:
        try:
            cur.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            result = cur.fetchone()
            count = result['count']
            total_records += count

            if count > 0:
                logger.info(f"✅ {display_name:25s}: {count:>10,} records")
            else:
                logger.warning(f"⚠️  {display_name:25s}: 0 records (table exists but empty)")
                all_good = False

        except Exception as e:
            logger.error(f"❌ {display_name:25s}: Table not found")
            all_good = False

    logger.info("=" * 70)
    logger.info(f"📊 Total Bronze Layer Records: {total_records:,}")
    logger.info("")

    cur.close()

    if not all_good:
        logger.warning("⚠️  Some raw tables are missing or empty!")
        logger.warning("💡 Run 'python run_smart_etl.py' first to load raw data")

        response = input("\n❓ Continue anyway? (y/N): ")
        if response.lower() != 'y':
            logger.info("❌ Deployment cancelled")
            sys.exit(1)

    return all_good


def get_layer_stats(conn):
    """Get statistics for each layer"""
    logger.info("📊 Data Warehouse Statistics")
    logger.info("=" * 70)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    stats = {}

    # Bronze layer
    bronze_tables = ['raw_daft_listings', 'raw_cso_rent', 'raw_cso_cpi', 'raw_cso_population', 'raw_cso_income']
    bronze_count = 0
    for table in bronze_tables:
        try:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            bronze_count += cur.fetchone()['count']
        except:
            pass

    stats['bronze'] = bronze_count

    # Silver layer (views)
    try:
        cur.execute("SELECT COUNT(*) as count FROM silver.stg_daft_listings")
        stats['silver_daft'] = cur.fetchone()['count']
    except:
        stats['silver_daft'] = 0

    # Gold dimensions
    gold_dims = ['dim_date', 'dim_county', 'dim_property_type', 'dim_market_segment']
    gold_dim_count = 0
    for table in gold_dims:
        try:
            cur.execute(f"SELECT COUNT(*) as count FROM gold.{table}")
            gold_dim_count += cur.fetchone()['count']
        except:
            pass

    stats['gold_dimensions'] = gold_dim_count

    # Gold facts
    gold_facts = ['fact_rental_listings', 'fact_market_summary', 'fact_affordability',
                  'fact_economic_indicators', 'fact_price_movements']
    gold_fact_count = 0
    for table in gold_facts:
        try:
            cur.execute(f"SELECT COUNT(*) as count FROM gold.{table}")
            gold_fact_count += cur.fetchone()['count']
        except:
            pass

    stats['gold_facts'] = gold_fact_count

    cur.close()

    # Display stats
    logger.info(f"🥉 BRONZE (Raw):           {stats['bronze']:>10,} records")
    logger.info(f"🥈 SILVER (Cleaned):       {stats['silver_daft']:>10,} records")
    logger.info(f"🥇 GOLD Dimensions:        {stats['gold_dimensions']:>10,} records")
    logger.info(f"🥇 GOLD Facts:             {stats['gold_facts']:>10,} records")
    logger.info("=" * 70)
    logger.info("")

    return stats


def main():
    """Main deployment function"""
    start_time = datetime.now()

    print("\n" + "=" * 70)
    print("🏗️  IRELAND HOUSING DATA WAREHOUSE DEPLOYMENT")
    print("=" * 70)
    print("Architecture: Medallion (Bronze → Silver → Gold)")
    print("Layers: Raw → Cleaned Views → Star Schema (4 Dims + 5 Facts)")
    print("=" * 70)
    print("")

    # Connect to database
    logger.info("🔌 Connecting to database...")
    conn = get_db_connection()
    logger.info("✅ Connected successfully")
    logger.info("")

    # Check prerequisites
    has_data = check_prerequisites(conn)

    # Execute SQL scripts in order
    logger.info("🚀 Deploying Data Warehouse...")
    logger.info("=" * 70)
    logger.info("")

    success_count = 0
    failed_scripts = []

    for script_path in SQL_SCRIPTS:
        if os.path.exists(script_path):
            if execute_sql_file(conn, script_path):
                success_count += 1
            else:
                failed_scripts.append(script_path)
        else:
            logger.error(f"❌ Script not found: {script_path}")
            failed_scripts.append(script_path)

    # Get final statistics
    logger.info("=" * 70)
    logger.info("📈 DEPLOYMENT COMPLETE")
    logger.info("=" * 70)
    logger.info("")

    stats = get_layer_stats(conn)

    # Summary
    logger.info("=" * 70)
    logger.info("📋 DEPLOYMENT SUMMARY")
    logger.info("=" * 70)
    logger.info(f"✅ Scripts Executed: {success_count}/{len(SQL_SCRIPTS)}")

    if failed_scripts:
        logger.error(f"❌ Failed Scripts: {len(failed_scripts)}")
        for script in failed_scripts:
            logger.error(f"   - {script}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info(f"⏱️  Duration: {duration:.2f} seconds")
    logger.info("=" * 70)

    if success_count == len(SQL_SCRIPTS):
        logger.info("🎉 SUCCESS: Data warehouse deployed successfully!")
        logger.info("")
        logger.info("Next Steps:")
        logger.info("1. Query gold layer tables: gold.fact_rental_listings, gold.fact_market_summary, etc.")
        logger.info("2. Connect Power BI to gold layer for dashboards")
        logger.info("3. Refresh data: Run 'python run_smart_etl.py' then re-run this script")
    else:
        logger.error("❌ FAILED: Some scripts failed to execute")
        sys.exit(1)

    conn.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n❌ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n❌ Deployment failed: {e}")
        sys.exit(1)
