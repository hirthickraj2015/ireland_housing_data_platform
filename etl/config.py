"""
Configuration management for Irish Housing Data Platform
Loads environment variables and provides centralized config access
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class for all ETL processes"""

    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "postgres")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

    # Connection String
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # Data Sources
    DAFT_BASE_URL = os.getenv("DAFT_BASE_URL", "https://www.daft.ie")
    CSO_API_BASE = "https://data.cso.ie"
    PROPERTY_REGISTER_URL = "https://www.propertypriceregister.ie"
    ECB_API_BASE = "https://sdw.ecb.europa.eu"

    # Scraping Settings
    USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    SCRAPE_DELAY_SECONDS = int(os.getenv("SCRAPE_DELAY_SECONDS", 2))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", 30))

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Project Paths
    PROJECT_ROOT = Path(__file__).parent.parent
    ETL_DIR = PROJECT_ROOT / "etl"
    SQL_DIR = PROJECT_ROOT / "sql"
    DBT_DIR = PROJECT_ROOT / "dbt"
    LOGS_DIR = PROJECT_ROOT / "logs"

    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
        missing = [var for var in required_vars if not getattr(cls, var)]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True


# Create logs directory if it doesn't exist
Config.LOGS_DIR.mkdir(exist_ok=True)
