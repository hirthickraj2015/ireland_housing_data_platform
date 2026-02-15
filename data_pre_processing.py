import pandas as pd
from generic_tools import time_function, crb_number_months, get_config

pd.options.mode.chained_assignment = None
col_head = get_config()['column_headers']
static_period = crb_number_months()


class DataPreProcessing:

    def __init__(self):
        pass


    @time_function
    def spread_invoices_over_months(self, df, spread_cols=['arr']):
        """
        Spread invoices over months in the provided DataFrame based on subscription start and end dates.

        This function performs the following steps:
        1. Validates that the 'subscription_start_date' and 'subscription_end_date' columns are in datetime format.
        2. Calculates the minimum and maximum invoice date columns for the month spine.
        3. Creates a date spine containing all months within the range of the minimum and maximum invoice dates.
        4. Performs a cross join with the original DataFrame to spread invoices over months.
        5. Sets specified spread columns to 0 where the month is outside the invoice date range.

        :param df: pandas DataFrame
            The DataFrame containing subscription information to spread over months.
        :param spread_cols: list, default=['arr']
            The list of columns to be spread over months.

        :return: pandas DataFrame
            The DataFrame with invoices spread over months.
        """
        if not pd.api.types.is_datetime64_any_dtype(df['subscription_start_date']):
            raise ValueError(f"The subscription_state_date column is not in datetime format.")

        if not pd.api.types.is_datetime64_any_dtype(df['subscription_end_date']):
            raise ValueError(f"The subscription_end_date column is not in datetime format.")

        # calculate the min invoice and max invoice date columns for the month spine
        min_date = df['subscription_start_date'].min()
        max_date = df['subscription_end_date'].max() + pd.DateOffset(months=12)

        # create date spine
        date_spine = pd.DataFrame(data={'month': pd.date_range(start=min_date, end=max_date, freq='MS')})

        # cross join with invoice data to spread invoices
        df = df.merge(date_spine, how='cross')

        # set spread columns to 0 where the month is outside the invoice date range
        for col in spread_cols:
            df.loc[~((df['month'] >= df['subscription_start_date']) & (df['month'] <= df['subscription_end_date'])), col] = 0

        # TODO: add in revenue before / after checks

        return df


    @time_function
    def fill_month_completeness(self, df):
        """
        Fill month completeness in the provided DataFrame by adding missing rows for each primary key and month
        combination.

        This function performs the following steps:
        1. Calculates the minimum and maximum month values from the input DataFrame.
        2. Generates a date spine containing all months within the calculated range.
        3. Creates a DataFrame with primary key columns and unique combinations.
        4. Performs a cross join between the primary key DataFrame and the date spine.
        5. Joins the resulting DataFrame onto the full input DataFrame, including missing rows.
        6. Selects only the rows where the join hasn't worked (missing rows).
        7. Adjusts the shape and renames columns for the missing rows.
        8. Appends the missing rows to the original DataFrame.

        :param df: pandas DataFrame
            The DataFrame with missing rows to be filled for month completeness.

        :return: pandas DataFrame
            The DataFrame with missing rows filled for month completeness.
        """
        month_max = df['month'].max() + pd.DateOffset(months=12)
        month_min = df['month'].min()

        # Generate list of dates
        date_spine = pd.DataFrame(data={'month_gen': pd.date_range(start=month_min, end=month_max, freq='MS')})

        # generate primary key dataframe
        key_columns = col_head['primary_key_columns']
        df_pk = df[['primary_key'] + key_columns].copy()
        df_pk = df_pk.drop_duplicates()

        # Cross join list of primary keys with list of dates
        df_merged = pd.merge(df_pk, date_spine, how='cross')

        # Join onto full dataframe
        df_merged_2 = pd.merge(df_merged, df, how='left', left_on=['primary_key', 'month_gen'] + key_columns,
                               right_on=['primary_key', 'month'] + key_columns)

        # Select only rows where join hasn't worked
        df_merged_2 = df_merged_2[df_merged_2['month'].isnull()]

        # Fix shape of these new rows and rename columns
        df_merged_2['arr'] = 0
        df_merged_2 = df_merged_2.drop(columns='month')
        df_merged_2 = df_merged_2.rename(columns={'month_gen':'month'
                                                  })

        # Append these rows to the dataframe
        df = pd.concat([df, df_merged_2], axis=0)

        return df