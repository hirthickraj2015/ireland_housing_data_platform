"""
Logging configuration for the ETL pipeline
Uses loguru for better logging experience
"""
import sys
from loguru import logger
from etl.config import Config


def setup_logger():
    """Configure loguru logger with appropriate settings"""

    # Remove default handler
    logger.remove()

    # Console handler with colors
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=Config.LOG_LEVEL,
        colorize=True
    )

    # File handler for all logs
    logger.add(
        Config.LOGS_DIR / "etl_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # Rotate at midnight
        retention="30 days",
        compression="zip"
    )

    # Error-only file handler
    logger.add(
        Config.LOGS_DIR / "errors_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="90 days",
        compression="zip"
    )

    return logger


def get_logger(name: str):
    """Get a logger instance with the given name"""
    return logger.bind(name=name)


# Initialize logger on import
setup_logger()
