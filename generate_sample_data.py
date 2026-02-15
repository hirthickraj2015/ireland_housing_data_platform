"""
Sample Input Data Generator for ARR Reporting Framework

Generates random input data that can be fed into main.py for processing.
The framework will calculate churn, upsell, downsell, cross-sell, etc.

Usage:
    python generate_sample_data.py --records 1000 --years 2 --output data/sample_input.csv
"""

import argparse
import random
from datetime import datetime
import pandas as pd
import numpy as np


# Sample data pools for random generation
PRODUCT_FAMILIES = ['Analytics', 'Security', 'Integration', 'Automation', 'AI/ML']
PRODUCT_SUB_FAMILIES = {
    'Analytics': ['Analytics - Reporting', 'Analytics - BI', 'Analytics - Dashboards'],
    'Security': ['Security - Firewall', 'Security - Identity', 'Security - Compliance'],
    'Integration': ['Integration - API', 'Integration - ETL', 'Integration - Sync'],
    'Automation': ['Automation - Workflow', 'Automation - RPA', 'Automation - Tasks'],
    'AI/ML': ['AI/ML - Predictive', 'AI/ML - NLP', 'AI/ML - Vision']
}
PRODUCTS = {
    'Analytics': ['Dashboard Pro', 'Report Builder', 'Data Explorer'],
    'Security': ['Firewall Plus', 'Identity Manager', 'Threat Detection'],
    'Integration': ['API Gateway', 'Data Sync', 'Connector Hub'],
    'Automation': ['Workflow Engine', 'Task Scheduler', 'Process Bot'],
    'AI/ML': ['Predictive Suite', 'NLP Toolkit', 'Vision API']
}

COUNTRIES = ['USA', 'UK', 'Germany', 'France', 'Canada', 'Australia', 'Japan', 'Brazil']
REGIONS = {
    'USA': 'North America', 'Canada': 'North America',
    'UK': 'Europe', 'Germany': 'Europe', 'France': 'Europe',
    'Australia': 'APAC', 'Japan': 'APAC',
    'Brazil': 'LATAM'
}
SEGMENTS = ['Enterprise', 'Mid-Market', 'SMB', 'Startup']
CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'AUD']


def generate_months(start_year: int, num_years: int) -> list:
    """Generate list of month dates."""
    months = []
    for year in range(start_year, start_year + num_years):
        for month in range(1, 13):
            months.append(datetime(year, month, 1))
    return months


def generate_sample_input(
    num_records: int,
    num_years: int,
    num_customers: int = None,
    num_products: int = None,
    start_year: int = None,
    output_path: str = None,
    seed: int = None
) -> pd.DataFrame:
    """
    Generate random input data for the ARR reporting framework.

    Parameters:
    - num_records: Total number of records to generate
    - num_years: Number of years of data
    - num_customers: Number of unique customers (default: num_records // 20)
    - num_products: Number of unique products (default: 15)
    - start_year: Starting year (default: current year - num_years)
    - output_path: Path to save CSV (optional)
    - seed: Random seed for reproducibility

    Returns:
    - DataFrame with input data
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    if start_year is None:
        start_year = datetime.now().year - num_years

    if num_customers is None:
        num_customers = max(10, num_records // 20)

    if num_products is None:
        num_products = 15

    # Generate month list
    months = generate_months(start_year, num_years)

    print(f"Generating sample input data...")
    print(f"  - Records: {num_records}")
    print(f"  - Customers: {num_customers}")
    print(f"  - Products: {num_products}")
    print(f"  - Period: {months[0].strftime('%Y-%m')} to {months[-1].strftime('%Y-%m')}")

    # Pre-generate customer pool
    customers = []
    for i in range(1, num_customers + 1):
        country = random.choice(COUNTRIES)
        customers.append({
            'customer_id': f'CUST-{i:05d}',
            'customer_name': f'Customer {i}',
            'country': country,
            'region': REGIONS[country],
            'segment': random.choice(SEGMENTS),
            'currency': random.choice(CURRENCIES)
        })

    # Pre-generate product pool
    products = []
    for i in range(1, num_products + 1):
        family = random.choice(PRODUCT_FAMILIES)
        sub_family = random.choice(PRODUCT_SUB_FAMILIES[family])
        product_name = random.choice(PRODUCTS[family])
        products.append({
            'product_id': f'PROD-{i:04d}',
            'product_name': product_name,
            'product_family': family,
            'product_sub-family': sub_family
        })

    # Generate unique customer-product-month combinations
    # Each customer subscribes to random products for consecutive months
    records = []
    used_combinations = set()

    records_per_customer = max(1, num_records // num_customers)

    for customer in customers:
        # Each customer gets a subset of products
        customer_products = random.sample(products, min(random.randint(1, 3), len(products)))

        # Determine start month for this customer (random point in timeline)
        start_idx = random.randint(0, max(0, len(months) - records_per_customer // len(customer_products)))

        for product in customer_products:
            # Customer has this product for some consecutive months
            num_months_active = random.randint(3, min(12, len(months) - start_idx))

            # Random base ARR based on segment
            segment = customer['segment']
            if segment == 'Enterprise':
                base_arr = random.uniform(50000, 500000)
            elif segment == 'Mid-Market':
                base_arr = random.uniform(10000, 100000)
            elif segment == 'SMB':
                base_arr = random.uniform(1000, 25000)
            else:  # Startup
                base_arr = random.uniform(500, 10000)

            for i in range(num_months_active):
                month_idx = start_idx + i
                if month_idx >= len(months):
                    break

                month = months[month_idx]
                combo_key = (customer['customer_id'], product['product_id'], month.strftime('%m/%d/%Y'))

                if combo_key in used_combinations:
                    continue
                used_combinations.add(combo_key)

                # ARR can vary slightly month to month (simulate upsell/downsell)
                arr_variation = random.uniform(0.9, 1.1)
                arr = base_arr * arr_variation

                records.append({
                    'customer_id': customer['customer_id'],
                    'customer_name': customer['customer_name'],
                    'product_family': product['product_family'],
                    'product_sub-family': product['product_sub-family'],
                    'product_id': product['product_id'],
                    'product_name': product['product_name'],
                    'month': month.strftime('%d/%m/%Y'),  # UK format DD/MM/YYYY
                    'arr': round(arr, 2),
                    'is_recurring': 1,
                    'currency': customer['currency'],
                    'country': customer['country'],
                    'region': customer['region'],
                    'segment': customer['segment']
                })

    df = pd.DataFrame(records)

    # Sort by customer, product, month
    df['_month_dt'] = pd.to_datetime(df['month'], format='%m/%d/%Y')
    df = df.sort_values(['customer_id', 'product_id', '_month_dt'])
    df = df.drop(columns=['_month_dt'])
    df = df.reset_index(drop=True)

    print(f"\nGenerated data summary:")
    print(f"  - Total records: {len(df)}")
    print(f"  - Unique customers: {df['customer_id'].nunique()}")
    print(f"  - Unique products: {df['product_id'].nunique()}")
    print(f"  - Unique months: {df['month'].nunique()}")
    print(f"  - ARR range: ${df['arr'].min():,.2f} - ${df['arr'].max():,.2f}")
    print(f"  - Total ARR: ${df['arr'].sum():,.2f}")

    if output_path:
        df.to_csv(output_path, index=False)
        print(f"\nData saved to: {output_path}")

    return df


def main():
    parser = argparse.ArgumentParser(
        description='Generate sample input data for the ARR reporting framework'
    )
    parser.add_argument(
        '--records', '-r',
        type=int,
        default=1000,
        help='Number of records to generate (default: 1000)'
    )
    parser.add_argument(
        '--years', '-y',
        type=int,
        default=2,
        help='Number of years of data (default: 2)'
    )
    parser.add_argument(
        '--customers', '-c',
        type=int,
        default=None,
        help='Number of unique customers (default: records/20)'
    )
    parser.add_argument(
        '--products', '-p',
        type=int,
        default=15,
        help='Number of unique products (default: 15)'
    )
    parser.add_argument(
        '--start-year', '-s',
        type=int,
        default=None,
        help='Starting year (default: current year - years)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='data/sample_input.csv',
        help='Output CSV file path (default: data/sample_input.csv)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for reproducibility'
    )

    args = parser.parse_args()

    generate_sample_input(
        num_records=args.records,
        num_years=args.years,
        num_customers=args.customers,
        num_products=args.products,
        start_year=args.start_year,
        output_path=args.output,
        seed=args.seed
    )


if __name__ == '__main__':
    main()
