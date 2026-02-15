import pandas as pd
import numpy as np
from generic_tools import get_config
from data_pre_processing import DataPreProcessing
import warnings

pd.options.mode.chained_assignment = None
col_head = get_config()['column_headers']
dpp = DataPreProcessing()

class DataPreChecks:

    def __init__(self):
        pass

    def check_month_completeness(self, df):
        """
        Check the completeness of the month data for each customer and product combination in the provided DataFrame.

        This function performs the following steps:
        1. Determines the minimum and maximum months present for each (customer_id, product_id) combination.
        2. Creates a reference table with a complete set of months within the overall date range of the dataset.
        3. Expands the original DataFrame to include all possible (customer_id, product_id, month) combinations using the reference table.
        4. Filters out irrelevant months for each (customer_id, product_id) combination based on the determined min and max months.
        5. Compares the reference dataset against the actual dates in the input DataFrame.
        6. If any dates are missing, it prints a message indicating the missing dates and suggests calling the 'fill_date_completeness' function.
           - The 'fill_date_completeness' function is called automatically if missing dates are detected.

        :param df: pandas DataFrame
            The DataFrame containing the month data to be checked for completeness.

        :return: pandas DataFrame
            The original DataFrame with potential adjustments made to ensure month completeness.
            If missing dates are detected, the 'fill_date_completeness' function is called to fill in the gaps.
        """
        # Find maximum and minimum month that an invoice should be present in the dataset
        df_grouped = df.groupby(['customer_id', 'product_id']).agg(min_month= ('month', np.min),
                                                                   max_month= ('month', np.max)).reset_index()

        # Create list of dates to make reference table
        max_date = df['month'].max()
        min_date = df['month'].min()
        date_spine = pd.DataFrame(data={'month': pd.date_range(start=min_date, end=max_date, freq='MS')})

        # Join on dates to existing table to ensure every customer has a relevant date row
        df_expanded = pd.merge(df_grouped, date_spine, how='cross')

        # Remove months that are not relevant to each customer
        df_expanded = df_expanded[(df_expanded['month'] <= df_expanded['max_month']) &
                                  (df_expanded['month'] >= df_expanded['min_month'])]

        # Select only relevant columns for comparison
        set_for_ref = list(str(df_expanded['customer_id']) + str(df_expanded['product_id']) + str(df_expanded['month']))
        input_set = list(str(df['customer_id']) + str(df['product_id']) + str(df['month']))

        # Compare the reference dataset against the dates that we have present. If dates are missing, this will be
        # flagged in the output to the reference
        missing_rows = [x for x in set_for_ref if x not in input_set]

        if missing_rows is not None:
            print(f"Following date lines are missing from the input: \n {missing_rows}")
            print("Calling fill_date_completeness function - if you do not wish to call this please stop the script"
                  "and fix the issue upstream")
            df = dpp.fill_month_completeness(df)

        else:
            print("All required dates are present")

        return df

    def check_columns_presence(self, df):
        """
        Checks if our necessary columns are present in the DataFrame.

        :param df: Input dataframe with all columns included
        :return: Will raise KeyError if some columns are not present
        """
        present_columns = set(df.columns)
        required_columns = set(col_head['required_columns'])

        missing_columns = required_columns - present_columns
        if required_columns.issubset(present_columns):
            print('All required columns are present for the customer revenue bridge analysis.')
        else:
            raise KeyError('Some columns are missing for the customer revenue bridge analysis. '
                            f'Missing columns: {missing_columns}')

    def process_month_column(self, df, month_col='month', date_format='US'):
        """
        Process the specified date column in the provided DataFrame, ensuring it matches the specified date format.

        :param df: pandas DataFrame
            The DataFrame containing the date column to be processed.
        :param month_col: str, default='month'
            The name of the column representing dates.
        :param date_format: str, default='US'
            The desired date format. Options are 'US' for mm/dd/yyyy or 'UK' for dd/mm/yyyy.

        :return: pandas DataFrame
            The original DataFrame with potential adjustments made to the date column:
            - If the specified date format is not 'US' or 'UK', a ValueError is raised.
            - If the date column does not match the specified format, a ValueError is raised.
            - The date column is converted to a pandas datetime object.
            - The date column is then trimmed to the first day of each month.
            The processed DataFrame is returned.
        """
        # Convert date format to dateutil parser format
        date_formats = {
            'US': 'mdy',
            'UK': 'dmy'
        }
        parser_format = date_formats.get(date_format.upper())
        if parser_format is None:
            raise ValueError("Invalid date format in parameter. Please specify 'US' or 'UK'.")

        # Check if the date column is in the specified format
        if parser_format == 'mdy':
            # Check if the date format is mm/dd/yyyy
            format_regex = r"^(0[1-9]|1[0-2])/(0[1-9]|[1-2][0-9]|3[0-1])/\d{4}$"
        elif parser_format == 'dmy':
            # Check if the date format is dd/mm/yyyy
            format_regex = r"^(0[1-9]|[1-2][0-9]|3[0-1])/(0[1-9]|1[0-2])/\d{4}$"
        else:
            raise ValueError("Invalid date format in parameter. Please specify 'US' or 'UK'.")

        if not df[month_col].str.match(format_regex).all():
            raise ValueError(f"The {month_col} column does not match the specified date format ({date_format}).")

        # Check and convert the date column to a pd datetime
        df[month_col] = pd.to_datetime(df[month_col], dayfirst=(parser_format == 'dmy'), errors='coerce')
        # trim to first of month
        df[month_col] = df[month_col].dt.to_period('M').dt.to_timestamp()

        return df


    def check_arr_column (self, df):
        """
        Check and handle the 'arr' column in the provided DataFrame.

        :param df: pandas DataFrame
            The DataFrame containing the 'arr' column to be checked and processed.

        :return: pandas DataFrame
            The original DataFrame with potential adjustments made to the 'arr' column:
            - If the 'arr' column is not of numeric type, a TypeError is raised.
            - If negative values are found in the 'arr' column, they are replaced with zero,
              and a warning is issued. The DataFrame is then returned.
        """
        # Check if revenue is a numeric type
        if not pd.api.types.is_numeric_dtype(df['arr']):
            raise TypeError(f"The '{arr}' column is not a numeric type.")

        # Check that revenue is positive - change to zero if not
        if (df['arr'] < 0).any():
            warnings.warn("the ARR column contains negative values. These have been set to zero but should be reviewed in the input data")
            df.loc[df['arr'] < 0, 'arr'] = 0

        return df
    
    
    def check_arr_negative_value(self, df):
        """
        Check if the 'arr' column in the provided DataFrame contains negative values.

        :param df: pandas DataFrame
            The DataFrame to be checked.

        :return: pandas DataFrame
            The original DataFrame if no negative values are found in the 'arr' column.
            Raises a ValueError if negative values are present.
        """
        # check if revenue is a number
        if (df['arr'] < 0):
            raise ValueError(f"The column ARR has negative value.")
        
        return df
    
    
        
    