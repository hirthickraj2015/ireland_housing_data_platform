#!/usr/bin/env python3
"""
Deploy raw tables to Neon PostgreSQL database
"""

import psycopg2
import os
from pathlib import Path

# Database connection parameters
DB_CONFIG = {
    'host': 'ep-nameless-cherry-abn7j2cl-pooler.eu-west-2.aws.neon.tech',
    'port': 5432,
    'database': 'neondb',
    'user': 'neondb_owner',
    'password': 'npg_e3y6gIFNHsaD',
    'sslmode': 'require'
}

def deploy_tables():
    """Deploy all raw tables and schemas"""

    print("🚀 Starting table deployment to Neon PostgreSQL...")
    print("=" * 70)

    # Read SQL file
    sql_file = Path('sql/create_raw_tables.sql')
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        return False

    with open(sql_file, 'r') as f:
        sql_content = f.read()

    try:
        # Connect to database
        print(f"\n📡 Connecting to Neon PostgreSQL at {DB_CONFIG['host']}...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()

        # Test connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"   PostgreSQL version: {version.split(',')[0]}")

        # Create dbt schemas
        print("\n📁 Creating dbt schemas...")
        schemas = ['staging', 'marts', 'analytics']
        for schema in schemas:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
            print(f"   ✓ Schema '{schema}' created")

        # Deploy raw tables
        print("\n📊 Deploying raw tables...")
        cursor.execute(sql_content)
        print("   ✓ All raw tables deployed successfully")

        # Verify tables
        print("\n🔍 Verifying table creation...")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'raw_%'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        print(f"   Found {len(tables)} raw tables:")
        for table in tables:
            print(f"   ✓ {table[0]}")

        # Check raw_daft_listings field count
        cursor.execute("""
            SELECT count(*)
            FROM information_schema.columns
            WHERE table_name = 'raw_daft_listings';
        """)
        field_count = cursor.fetchone()[0]
        print(f"\n   📋 raw_daft_listings has {field_count} fields (expected 38+)")

        if field_count >= 38:
            print("   ✅ Field count validated!")
        else:
            print(f"   ⚠️  Expected 38+ fields, got {field_count}")

        # Close connection
        cursor.close()
        conn.close()

        print("\n" + "=" * 70)
        print("✅ Deployment completed successfully!")
        return True

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = deploy_tables()
    exit(0 if success else 1)
