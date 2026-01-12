#!/usr/bin/env python3
"""
Test script to scrape ALL available Daft listings
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from etl.scrapers.daft_scraper_automated_async import DaftScraperAutomatedAsync

async def test_full_scrape():
    """Test scraping ALL available listings"""
    print("🧪 Testing FULL Daft Scrape (ALL available listings)")
    print("=" * 60)

    async with DaftScraperAutomatedAsync(headless=True) as scraper:
        print("\n🔄 Starting scrape of ALL available listings...")
        print("   This may take several minutes depending on total listings...")

        listings = await scraper.scrape_all_listings(max_pages=50)  # Safety limit for testing

        print(f"\n✅ Scrape completed!")
        print(f"   Total listings collected: {len(listings)}")

        if listings:
            # Show some stats
            print("
📊 Sample listings:"            for i, listing in enumerate(listings[:3]):
                print(f"   {i+1}. {listing.get('title', 'N/A')} - €{listing.get('price', 'N/A')}")

            print(f"   ... and {len(listings) - 3} more listings")

if __name__ == "__main__":
    asyncio.run(test_full_scrape())