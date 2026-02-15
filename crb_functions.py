import pandas as pd
import numpy as np
from generic_tools import time_function, calculate_month_difference, encoder, crb_number_months
from generic_tools import calculate_start_of_current_period, calculate_start_of_next_period, get_config

pd.options.mode.chained_assignment = None
config = get_config()
col_head = config['column_headers']
con = config['constants']
static_period = crb_number_months()
product_level = con['product_level'][0]


class CustomerRevenueBridgeImplementation:
    def __init__(self):
        pass

    @time_function
    def create_primary_key(self, df, primary_key_cols):
        """
        Function calculates primary key for customer, and encodes it to reduce file storage size
        :param df: The input dataframe to the CRB
        :param primary_key_cols: Specified in the config file - the columns that confine granularity of customer
        :return: The dataframe with the primary key added
        """
        df['primary_key'] = df[primary_key_cols].astype(str).agg(' '.join, axis=1)
        df = encoder(df, 'primary_key')

        return df

    @time_function
    def remove_non_recurring_rows(self, df):
        """
        Function removes non-recurring rows of data if column is present in the dataset
        :param df: Input dataframe
        :return: dataframe with non-recurring rows removed (if relevant)
        """
        if 'is_recurring' in list(df.columns):
            df = df[df['is_recurring'] == 1]

        return df

    def max_min_dates(self, df, level):
        """

        :param df:
        :return:
        """
        if level == 'customer':
            tag = ['customer_id']
        elif level == 'product':
            tag = ['customer_id', product_level]
        elif level == 'segment':
            tag = ['primary_key'] + list(col_head['primary_key_columns'])
        else:
            raise KeyError("Input value of level needs to equal one of: [customer, product, segment]")

        # Get start and end dates for the required level:
        start_end_dates = df.groupby(tag).agg(min=('month', np.min), max=('month', np.max)).reset_index()

        # Rename the start and end months
        start_end_dates = start_end_dates.rename(columns={'min': f'{level}_start_date',
                                                          'max': f'{level}_end_date'})
        # Add one month to get the customer churn month
        if level == 'customer' or level == 'product':
            start_end_dates[f'{level}_churn_date'] = start_end_dates[f'{level}_end_date'] + \
                                                     pd.DateOffset(months=1)

        return start_end_dates

    @time_function
    def calculate_segment_start_end_dates(self, df):
        """
        Calculate the start and end dates of revenue segments for each segment, customer, product in the DataFrame.
        Done by taking various aggregations of max and min dates and consolidating.

        :param df: The DataFrame to calculate segment/product/customer start and end dates.
        :return: df  The DataFrame with additional columns representing customer/ product/ segment start and end dates.
        """
        # Select only columns with non-zero revenue for group bys
        df_no_zeros = df.loc[(df['arr'] != 0)]

        # Calculate segment start_end dates
        segment_start_end_dates = self.max_min_dates(df_no_zeros, 'segment')

        # Create table that accounts for revenue corrections - sum arr at product customer month level
        df_with_rev_corrections = df_no_zeros.groupby(['customer_id', product_level, 'month']).agg( \
            sum=('arr', np.sum)).reset_index()
        # Rename these columns
        df_with_rev_corrections = df_with_rev_corrections.rename(columns={'sum': 'arr'})
        # Filter out months where revenue is 0 after revenue corrections
        df_with_rev_corrections_no_zeroes = df_with_rev_corrections.loc[(df_with_rev_corrections['arr'] != 0)]

        # Calculate product start/end dates
        product_start_end_dates = self.max_min_dates(df_with_rev_corrections_no_zeroes, 'product')

        # Calculate customer start/end dates
        customer_start_end_dates = self.max_min_dates(df_with_rev_corrections_no_zeroes, 'customer')

        # Merge customer start/end dates with product start/end dates
        customer_start_end_dates = pd.merge(product_start_end_dates,
                                            customer_start_end_dates,
                                            on='customer_id',
                                            how='left')

        # Merge product AND customer start / end dates with segment dates
        segment_start_end_dates = pd.merge(customer_start_end_dates,
                                           segment_start_end_dates,
                                           on=['customer_id', product_level],
                                           how='left')

        # Merge all dates back to original dataset using primary key
        df = pd.merge(df,
                      segment_start_end_dates,
                      on=['primary_key', 'customer_id', 'product_id'] + list(col_head['primary_key_columns']),
                      how='left')

        return df

    @time_function
    def trim_dataset(self, df):
        """
        Trim unnecessary rows from the Customer Revenue Booster (CRB) dataset based on calculated segment start and end dates.

        This function performs the following steps:
        1. Uses the "calculate_segment_start_end_dates" function to identify rows for trimming.
        2. For a fixed number of months (static_period=True), trims rows where the month is outside the segment start and end dates.
        3. For a variable offset (static_period=False), sets a custom end date as the next period following the segment end,
           and trims rows accordingly.
        4. Returns the modified input dataframe with unnecessary rows removed.

        :param df: pandas DataFrame
            The input CRB dataset with segment start and end dates calculated.
        :param static_period: bool
            Determines whether the CRB has a fixed number of months (True) or a variable period (False).

        :return: pandas DataFrame
            The input dataframe with unnecessary rows removed based on segment start and end dates.
        """
        if static_period:
            df = df[(df['month'] >= df['segment_start_date']) &
                    (df['month'] <= df['segment_end_date'] + pd.DateOffset(months=con['month_period']))]
        else:
            # Set custom end date as next period following segment end
            df['seg_end_date_period'] = calculate_start_of_next_period(df, 'segment_end_date')

            df = df[(df['month'] >= df['segment_start_date']) &
                    (df['month'] < df['seg_end_date_period'])]

            # Drop working column
            df = df.drop(columns=['seg_end_date_period'])

        return df

    @time_function
    def calculate_arr_changes(self, df):
        """
        Calculate the ARR change between the start of the period and the current month, adding a new column to the existing dataframe.

        This function performs the following steps:
        1. Sorts the dataframe by primary key and month.
        2. For a fixed number of months (static_period=True), calculates ARR change by shifting rows in the dataframe.
        3. For a variable offset (static_period=False), creates a new column indicating the start of the current period,
           merges a copy of the dataframe at the start of each period onto the original dataframe, and calculates ARR change.
        4. Returns the input dataframe with additional columns indicating ARR change over the CRB period.

        :param df: pandas DataFrame
            The input DataFrame to the Customer Revenue Booster (CRB) script.
        :param static_period: bool
            Determines whether the CRB has a fixed number of months (True) or a variable period (False).

        :return: pandas DataFrame
            The input dataframe with new fields added indicating ARR change over the CRB period.
        """
        # Sort the dataframe by primary key and month
        df = df.sort_values(['primary_key', 'month'], ascending=[True, True])

        if static_period:
            # For fixed number of months looking backwards
            df[f'arr_bop'] = df.groupby('primary_key')['arr'].shift(
                periods=con['month_period']).fillna(0)
            df[f'arr_delta'] = df['arr'] - df[f'arr_bop']
        else:
            # For variable offsets, found in YTD/QTD
            df['start_of_current_period'] = calculate_start_of_current_period(df, 'month')
            df_arr = df[['primary_key', 'month', 'arr']].rename(columns={'arr': f'arr_bop'})
            df = pd.merge(df,
                          df_arr,
                          how='left',
                          left_on=['primary_key', 'start_of_current_period'],
                          right_on=['primary_key', 'month'])
            df[f'arr_bop'] = df[f'arr_bop'].fillna(0)
            df[f'arr_delta'] = df['arr'] - df[f'arr_bop']
            df = df.drop(columns=['start_of_current_period','month_y']).rename(columns={'month_x': 'month'})

        return df

    @time_function
    def create_arr_deltas(self, df):
        """
        Convert CRB bucket flags into ARR change amounts by multiplying the flags with the period ARR change.

        This function requires the prior execution of the 'calculate_arr_changes' function. ARR buckets are identified based on
        the existence of columns containing the word 'flag' but not the word 'existing.'

        :param df: pandas DataFrame
            The input DataFrame representing the Customer Revenue Booster (CRB). Required columns include 'arr_delta'
            and flags for any ARR movement buckets to be identified.

        :return: pandas DataFrame
            The modified input DataFrame with additional columns for each ARR movement bucket flag, representing the ARR change amounts.
        """
        # create list of flag columns we want to create deltas for
        flag_columns = [col for col in df.columns if 'flag' in col and 'existing' not in col]

        # for loop to create delta columns for each of the flag columns
        for col in flag_columns:
            new_col_name = col.replace('flag', 'delta')
            df[new_col_name] = df[col] * df[f'arr_delta']

        return df

    @time_function
    def drop_dimensions_columns(self, df):
        """
        Drop dimension columns from the provided DataFrame and create a separate dimension DataFrame.

        This function performs the following steps:
        1. Maps dimension columns to new names using a predefined dictionary.
        2. Drops dimension columns from the input DataFrame and creates a new DataFrame containing only the primary key and dimension columns.
        3. Removes duplicate rows from the new dimension DataFrame.
        4. Returns the modified input DataFrame with dropped dimension columns and the new dimension DataFrame.

        :param df: pandas DataFrame
            The DataFrame containing dimension columns to be dropped.

        :return: Tuple[pandas DataFrame, pandas DataFrame]
            The modified input DataFrame without dimension columns and the new dimension DataFrame containing primary key and dimension columns.
        """
        # Map dimension columns to new names
        dict = col_head['dimension_columns']
        df = df.rename(columns=dict)

        # Drop dimension columns and create new mapping dataset
        dim_columns = [x for x in df.columns if 'Dimension' in x]
        df_dim = df[['primary_key'] + dim_columns].copy()
        df_dim = df_dim.drop_duplicates()
        df = df.drop(columns=dim_columns)

        return df, df_dim

    @time_function
    def create_flattened_output(self, df, df_dim):
        """
        Create a flattened output DataFrame for Tableau visualization based on the input DataFrame and dimension DataFrame.

        This function performs the following steps:
        1. Filters the input DataFrame to include data only for the recent time period.
        2. Renames columns based on the Alteryx template using column mapping in the configuration.
        3. Creates new columns needed for Tableau, including 'Customer_Cohort,' 'Customer_Cohort_Year,' and 'Customer_Tenure.'
        4. Fills in extra columns ('Customer_name' and 'Product_family') if they do not exist in the input DataFrame.
        5. Joins back in dimension columns from the provided dimension DataFrame.
        6. Returns the resulting flattened output DataFrame for Tableau visualization.

        :param df: pandas DataFrame
            The input DataFrame containing data for Tableau visualization.
        :param df_dim: pandas DataFrame
            The DataFrame containing dimensions to be joined with the input DataFrame.

        :return: pandas DataFrame
            The flattened output DataFrame for Tableau visualization.
        """
        # Filter month only for recent time period
        df = df.loc[df['month'] >= pd.to_datetime('2012-01-01')]
        # Rename columns to match the Alteryx template - using mapping in config
        df = df.rename(columns=col_head['tableau_col_mapping'])

        # create new columns needed for Tableau:
        df['Customer_Cohort'] = df['Customer_Join_Month']
        df['Customer_Cohort_Year'] = df['Customer_Cohort'].dt.year
        df['Customer_Tenure'] = calculate_month_difference(df, 'Customer_Join_Month', 'Month')
        # df['Product_Churn_Month'] = df['Product_Last_month'] + pd.DateOffset(months=12) - feel like this is wrong?

        # create and fill in extra columns if they don't exist:
        for col in ['Customer_name', 'Product_family']:
            if col in df.columns:
                pass
            else:
                df[col] = np.nan

        # join back in dimensions
        df = pd.merge(df, df_dim, on=['primary_key'], how='left')

        return df

    @time_function
    def create_waterfall_output(self, df):
        """
        Create a waterfall output DataFrame based on the input DataFrame with ARR-related columns.

        This function performs the following steps:
        1. Defines the list of columns to keep as IDs before the melt operation.
        2. Calculates Net Revenue Retention (NRR), Gross Revenue Retention (GRR), and reversed columns.
        3. Renames columns for waterfall output based on the specified period.
        4. Melts rows for waterfall output, creating columns for 'Value type' and 'Value yearly.'
        5. Removes rows where 'Value yearly' is zero.
        6. Returns the resulting waterfall output DataFrame.

        :param df: pandas DataFrame
            The input DataFrame containing ARR-related columns.

        :return: pandas DataFrame
            The waterfall output DataFrame with 'Value type' and 'Value yearly' columns.
        """
        # Create list of columns to keep as IDs before the melt
        dimensions = [x for x in df.columns if 'Dimension' in x]
        id_vars = col_head['tableau_id_columns'] + dimensions
        # id_vars = [col for sublist in cols_for_waterfall for col in sublist]
        print(id_vars)
        # calculate NRR depending on period
        df['NRR'] = df['ARR_BOP'] + df['Delta_Churn'] + df['Delta_Downsell'] + df['Delta_Downgrade'] + \
                    df['Delta_Upsell'] + df['Delta_Cross_Sell']

        # calculate GRR depending on period
        df['GRR'] = df['ARR_BOP'] + df['Delta_Churn'] + df['Delta_Downsell'] + df['Delta_Downgrade']

        # calculate reversed columns:
        df['GRR_reversed'] = -df['GRR']
        df['NRR_reversed'] = -df['NRR']
        df['EoP_reversed'] = -df['ARR']

        # rename columns for waterfall output (depending on period)
        rename_dict = {'ARR_BOP': 'BoP ARR',
                       'Delta_Churn': 'Churn',
                       'Delta_Downsell': 'Downsell',
                       'Delta_Downgrade': 'Downgrade',
                       'Delta_Upsell': 'Upsell',
                       'Delta_New_Customer': 'New Customers',
                       'Delta_Cross_Sell': 'Cross-sell',
                       'ARR': 'EoP ARR'}

        # melt rows for waterfall output
        df = df.rename(columns=rename_dict)
        cols_to_melt = []
        for i in rename_dict:
            cols_to_melt.append(rename_dict[i])
        cols_to_melt = cols_to_melt + ['GRR', 'NRR', 'NRR_reversed', 'GRR_reversed', 'EoP_reversed']

        waterfall_df = df.melt(id_vars=id_vars,
                               value_vars=cols_to_melt,
                               var_name='Value type',
                               value_name='Value yearly')

        # remove rows where value yearly = 0
        waterfall_df = waterfall_df.loc[waterfall_df['Value yearly'] != 0]

        # rename 1 column for tableau that cannot be in mapping file to allow for date flexibility
        # waterfall_df = waterfall_df.rename(columns={'ARR_1mo_ago': 'ARR_LM'})

        return waterfall_df
