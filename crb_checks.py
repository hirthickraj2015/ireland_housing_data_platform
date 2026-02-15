import pandas as pd
import numpy as np
from generic_tools import time_function, get_config
import numbers

pd.options.mode.chained_assignment = None
con = get_config()['constants']


class CustomerRevenueBridgeChecks:
    def __init__(self):
        pass

    @staticmethod
    def check_primary_key_uniqueness(df, primary_key_col='primary_key', month_col='month', sample_size=1):
        #@TODO - check this function for cleanness
        """
        Check the uniqueness of the primary key and month combination in the provided DataFrame.

        This function performs the following checks:
        1. Concatenates the primary key and month columns to create a new combined key column.
        2. Identifies and returns any duplicate combined keys.
        3. Raises a ValueError if duplicate combined keys are found, indicating non-unique primary key and month combinations.

        :param df: pandas DataFrame
            The DataFrame to check for primary key and month uniqueness.
        :param primary_key_col: str, default='primary_key'
            The name of the column representing the primary key.
        :param month_col: str, default='month'
            The name of the column representing dates.
        :param sample_size: int, default=1
            The number of duplicate keys to display as a sample in case of non-uniqueness.

        :return: pandas Series
            A Series containing duplicate combined keys if found; otherwise, an empty Series.
            Prints a message indicating the uniqueness status of the primary key and month combination.
        """
        # Create a copy of the input DataFrame
        df_copy = df.copy()
        # Concatenate primary key and month columns to create a new column
        df_copy['combined_key'] = df_copy[primary_key_col].astype(str) + '_' + df_copy[month_col].astype(str)

        # Find duplicate combined keys
        duplicate_keys = df_copy[df_copy['combined_key'].duplicated(keep=False)]['combined_key']

        if duplicate_keys.empty:
            print("Primary key and month combination is unique.")
            non_unique_primary_keys = []
        else:
            raise ValueError('primary keys not unique')

        return duplicate_keys

    def check_no_positive_churn(self, df):
        """
        Check the correctness of the churn and product churn values in the provided DataFrame.

        This function performs the following checks:
        1. Identifies and prints customers with positive values in the 'Delta_Churn' column.
        2. Raises a ValueError if any customers have positive churn values.

        3. Identifies and prints customers with positive values in the 'Delta_Downgrade' column.
        4. Raises a ValueError if any customers have positive product churn values.

        :param df: pandas DataFrame
            The DataFrame containing churn and product churn data.

        :return: None
            This function primarily performs validation checks and prints information about the correctness of churn and product churn values.
        """
        df_churn = df[df['Delta_Churn'] > 0].drop_duplicates()
        if len(df_churn) > 0:
            print(df_churn.head())
            raise ValueError('Customers in the dataset have positive churn')

        df_prod_churn = df[df['Delta_Downgrade'] > 0].drop_duplicates()
        if len(df_prod_churn) > 0:
            print(df_prod_churn.head())
            raise ValueError('Customers in the dataset have positive product churn')

    def check_no_negative_new_logo(self, df):
        """
        Check the correctness of the new logo and cross-sell values in the provided DataFrame.

        This function performs the following checks:
        1. Identifies and prints customers with negative values in the 'Delta_New_Customer' column.
        2. Raises a ValueError if any customers have negative new logo values.

        3. Identifies and prints customers with negative values in the 'Delta_Cross_Sell' column.
        4. Raises a ValueError if any customers have negative cross-sell values.

        :param df: pandas DataFrame
            The DataFrame containing new logo and cross-sell data.

        :return: None
            This function primarily performs validation checks and prints information about the correctness of new logo and cross-sell values.
        """
        df_new = df[df['Delta_New_Customer'] < 0].drop_duplicates()
        if len(df_new) > 0:
            print(df_new.head())
            raise ValueError('Customers in the dataset have negative new logo.')

        df_cross = df[df['Delta_Cross_Sell'] < 0].drop_duplicates()
        if len(df_cross) > 0:
            print(df_cross.head())
            raise ValueError('Customers in the dataset have negative cross-sell.')

    def check_upsell_downsell_direction(self, df):
        """
        Check the correctness of the upsell and downsell direction in the provided DataFrame.

        This function performs the following checks:
        1. Identifies and prints customers with negative upsell values in the 'Delta_Upsell' column.
        2. Raises a ValueError if any customers have negative upsell values.

        3. Identifies and prints customers with positive downsell values in the 'Delta_Downsell' column.
        4. Raises a ValueError if any customers have positive downsell values.

        :param df: pandas DataFrame
            The DataFrame containing upsell and downsell data.

        :return: None
            This function primarily performs validation checks and prints information about the correctness of upsell and downsell directions.
        """
        df_upsell = df[df['Delta_Upsell'] < 0].drop_duplicates()
        if len(df_upsell) > 0:
            print(df_upsell.head())
            raise ValueError('Customers in the dataset have negative upsell.')

        df_downsell = df[df['Delta_Downsell'] > 0].drop_duplicates()
        if len(df_downsell) > 0:
            print(df_downsell.head())
            raise ValueError('Customers in the dataset have positive downsell.')

    def check_waterfall_sums(self, df_initial, df_waterfall):
        """
        Check the correctness of the waterfall sums in comparison to the initial dataset.

        This function performs the following checks:
        1. Ensures that the sum of each category in the waterfall results in zero, excluding 'EoP ARR.'
        2. Sets non-recurring revenue in the initial dataset to zero if the 'is_recurring' column is present.
        3. Compares the annual totals of ARR between the initial dataset and the waterfall output.
        4. Raises a ValueError if the waterfall sums do not match the initial dataset.

        :param df_initial: pandas DataFrame
            The initial DataFrame containing the ARR data.
        :param df_waterfall: pandas DataFrame
            The DataFrame representing the waterfall output.

        :return: None
            This function primarily performs validation checks and prints information about the correctness of the waterfall sums.
        """
        # Check individual waterfalls sum up
        value_vars = ['BoP_ARR', 'Churn', 'Cross-sell', 'Downgrade', 'Downsell',
                      'Upsell', 'New Customers', 'NRR', 'GRR', 'NRR_reversed',
                      'GRR_reversed', 'EoP_reversed']

        # Remove EoP ARR: the negative EoP ARR field should mean that without this category the value will be 0
        df_waterfall_grouped = df_waterfall[df_waterfall['Value type'] != 'EoP ARR']

        df_waterfall_grouped = df_waterfall_grouped.groupby('primary_key').agg(check_sum=('Value yearly', np.sum))

        # Filter out any row where check_sum does not sum to zero
        df_waterfall_grouped['check_sum'] = df_waterfall_grouped['check_sum'].fillna(0)  # Replace NaN with 0
        df_waterfall_grouped = df_waterfall_grouped[df_waterfall_grouped['check_sum'].round(2) != 0]


        if len(df_waterfall_grouped) > 0:
            print(df_waterfall_grouped)
            raise ValueError("Waterfall does not sum to zero")

        # Confirm that all non-recurring revenue is set to zero
        if 'is_recurring' in list(df_initial.columns):
            df_initial.loc[df_initial['is_recurring'] != 1, 'arr'] = 0

        # Create 'year' variable for both datasets
        df_initial['year'] = pd.to_datetime(df_initial['month']).dt.year
        df_waterfall['year'] = pd.to_datetime(df_waterfall['Month']).dt.year

        # Find annual totals of waterfalls and check they match
        revenue_by_year = df_initial.groupby(['year'])['arr'].sum().round(2).to_dict()
        df_waterfall = df_waterfall[df_waterfall['Value type'] == 'EoP ARR']
        revenue_by_year_waterfall = df_waterfall.groupby(['year'])['Value yearly'].sum().round(2).to_dict()

        # Check for match
        if revenue_by_year == revenue_by_year_waterfall:
            print('Waterfall sums are equal.')
            print('Input:')
            print(revenue_by_year)
            print('\nOutput:')
            print(revenue_by_year_waterfall)
        else:
            ## If not match, begin error-checking process

            # Create dataframe revenue by year from initial dataset
            df_revenue_by_year = df_initial.groupby(['year', 'customer_id'])['arr'].sum().round(2).reset_index()

            # Create dataframe revenue by year but using output
            df_revenue_by_year_waterfall = df_waterfall.groupby(['year', 'Customer_ID'])['Value yearly'].sum().round(
                2).reset_index()

            # Join together two dfs to compare customer ARR
            df_merge = pd.merge(df_revenue_by_year,
                                df_revenue_by_year_waterfall,
                                how='left',
                                left_on=['year', 'customer_id'],
                                right_on=['year', 'Customer_ID']
                                )

            # Test new dataframe to find rows that do not match
            df_merge_no_match = df_merge[abs(df_merge['arr'] - df_merge['Value yearly']) > 0.1]
            print('Incorrect customers: ')
            print(df_merge_no_match)

            raise ValueError('Waterfall sums are not equal.')

    @time_function
    def check_config_time_period(self):
        """
        Check and validate the configuration settings related to the time period for the CRB.

        This function ensures that the selected CRB type in the configuration is valid and provides additional information based on the selected type.

        Raises KeyError or ValueError if the configuration is invalid.

        :return: None
            This function primarily performs validation checks and prints information about the selected CRB type and its parameters.
        """
        crb_type_options = ['number_of_months', 'YTD', 'QTD', 'FYTD', 'FQTD']
        if con['crb_type'] not in crb_type_options:
            raise KeyError(f'CRB type selected not valid - please choose one of {crb_type_options}.')

        if con['crb_type'] == 'number_of_months':
            if isinstance(con['month_period'], numbers.Number):
                print('CRB selected with period of last ', con['month_period'], ' months.')
            else:
                raise ValueError('Please select a valid number of months in the con file.')

        if con['crb_type'] == 'YTD':
            print('CRB selected for year to date, with year running from January-December.')

        if con['crb_type'] == 'QTD':
            print('CRB selected for quarter to date, with standard business quarters.')

        if con['crb_type'] in ['FYTD', 'FQTD']:
            if isinstance(con['fy_start_month'], numbers.Number) & (con['fy_start_month'] <= 12) & (
                    con['fy_start_month'] > 0):
                print(
                    f"CRB for {con['crb_type']} with FY starting in {pd.to_datetime(con['fy_start_month'],format='%m').strftime('%B')}.")
            else:
                raise ValueError('Please select a valid FY start month in the config file.')

    def summary_checks_mrr_data(self, df, customer_id_col, product_id_col, month_col, revenue_col):
        """
        Analyzes an invoice dataset and provides information about unique customers, date range, revenue by year,
        and number of customers with positive revenue in the last 12 months.

        Args:
            df (pandas.DataFrame): The invoice dataset.
            customer_id_col (str): The name of the column containing customer IDs.
            month_col (str): The name of the column representing the month.
            revenue_col (str): The name of the column representing the revenue.

        Returns:
            dict: A dictionary containing the analysis results.
                - 'unique_customers': The total number of unique customers.
                - 'unique_products': The total number of unique products.
                - 'date_range': A tuple of the minimum and maximum dates in the dataset.
                - 'revenue_by_year': A dictionary containing revenue by year.
                - 'customers_with_positive_revenue_last_12_months': The number of customers with positive revenue
                  in the last 12 months.
        """

        # Total number of unique customers
        unique_customers = df[customer_id_col].nunique()

        # Total number of unique products
        unique_products = df[product_id_col].nunique()
        if unique_products > 20:
            print('Number of unique products is high (<25), consider creating a product hierarchy to clean these up.')

        # Date range
        min_date = df[month_col].min()
        max_date = df[month_col].max()
        date_range = (min_date, max_date)

        # Revenue by year
        df['Year'] = pd.to_datetime(df[month_col]).dt.year
        revenue_by_year = df.groupby('Year')[revenue_col].sum().to_dict()

        # Number of customers with positive revenue in the last 12 months
        last_12_months = pd.to_datetime(max_date) - pd.DateOffset(months=11)
        recent_customers = df[df[month_col] >= last_12_months]
        customers_with_positive_revenue_last_12_months = recent_customers[recent_customers[revenue_col] > 0][
            customer_id_col].nunique()

        # Remove the temporary 'Year' column
        df.drop('Year', axis=1, inplace=True)

        # Prepare the analysis results as a dictionary
        results = {
            'unique_customers': unique_customers,
            'unique_products': unique_products,
            'date_range': date_range,
            'revenue_by_year': revenue_by_year,
            'customers_with_positive_revenue_last_12_months': customers_with_positive_revenue_last_12_months
        }

        return results
