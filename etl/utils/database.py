"""
Database utility functions for PostgreSQL operations
"""
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine
from contextlib import contextmanager
from typing import List, Dict, Any
import pandas as pd

from etl.config import Config
from etl.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self):
        self.config = Config
        self.engine = None

    def get_engine(self):
        """Get or create SQLAlchemy engine"""
        if not self.engine:
            self.engine = create_engine(
                self.config.DATABASE_URL,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )
            logger.info("Database engine created")
        return self.engine

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = psycopg2.connect(
            host=self.config.DB_HOST,
            port=self.config.DB_PORT,
            database=self.config.DB_NAME,
            user=self.config.DB_USER,
            password=self.config.DB_PASSWORD
        )
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a SELECT query and return results"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in cur.fetchall()]
                logger.info(f"Query executed successfully, {len(results)} rows returned")
                return results

    def execute_sql(self, sql: str, params: tuple = None):
        """Execute an INSERT/UPDATE/DELETE query"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                logger.info(f"SQL executed successfully, {cur.rowcount} rows affected")
                return cur.rowcount

    def bulk_insert(self, table: str, data: List[Dict], schema: str = None):
        """Bulk insert data into a table"""
        if not data:
            logger.warning("No data to insert")
            return 0

        schema = schema or self.config.DB_SCHEMA
        columns = list(data[0].keys())
        values = [[row.get(col) for col in columns] for row in data]

        insert_query = f"""
            INSERT INTO {schema}.{table} ({', '.join(columns)})
            VALUES %s
        """

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, insert_query, values)
                logger.info(f"Bulk insert: {len(data)} rows into {schema}.{table}")
                return len(data)

    def load_dataframe(self, df: pd.DataFrame, table: str,
                      schema: str = None, if_exists: str = 'append'):
        """Load a pandas DataFrame into database"""
        schema = schema or self.config.DB_SCHEMA
        engine = self.get_engine()

        rows_affected = df.to_sql(
            name=table,
            con=engine,
            schema=schema,
            if_exists=if_exists,
            index=False,
            method='multi',
            chunksize=1000
        )

        logger.info(f"DataFrame loaded: {len(df)} rows into {schema}.{table}")
        return rows_affected

    def truncate_table(self, table: str, schema: str = None):
        """Truncate a table"""
        schema = schema or self.config.DB_SCHEMA
        query = f"TRUNCATE TABLE {schema}.{table} CASCADE"
        self.execute_sql(query)
        logger.info(f"Table truncated: {schema}.{table}")

    def table_exists(self, table: str, schema: str = None) -> bool:
        """Check if a table exists"""
        schema = schema or self.config.DB_SCHEMA
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = %s
            )
        """
        result = self.execute_query(query, (schema, table))
        return result[0]['exists']


# Singleton instance
db = DatabaseManager()
