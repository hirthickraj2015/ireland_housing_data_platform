#!/usr/bin/env python3
"""
Test script for incremental Daft loading
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from etl.scrapers.daft_scraper_automated_async import DaftScraperAutomatedAsync

async def test_incremental_loading():
    """Test the incremental loading functionality"""
    print("🧪 Testing Incremental Daft Loading")
    print("=" * 50)

    async with DaftScraperAutomatedAsync(headless=True) as scraper:
        # Test checkpoint methods
        print("\n1. Testing checkpoint functionality...")

        # Check initial state
        checkpoint = scraper.get_last_checkpoint()
        print(f"   Initial checkpoint: {checkpoint}")

        # Test incremental scraping
        print("\n2. Testing incremental scraping...")
        listings = await scraper.scrape_listings_incremental(
            max_pages_incremental=1  # Small number for testing
        )

        print(f"   Scraped {len(listings)} listings")

        # Check updated checkpoint
        checkpoint = scraper.get_last_checkpoint()
        print(f"   Updated checkpoint: {checkpoint}")

        print("\n3. Testing second run (should be incremental)...")
        listings2 = await scraper.scrape_listings_incremental(
            max_pages_incremental=1
        )

        print(f"   Second run scraped {len(listings2)} listings")

        checkpoint2 = scraper.get_last_checkpoint()
        print(f"   Final checkpoint: {checkpoint2}")

    print("\n✅ Incremental loading test completed!")

if __name__ == "__main__":
    asyncio.run(test_incremental_loading())