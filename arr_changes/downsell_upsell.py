import pandas as pd
import numpy as np
from generic_tools import time_function, calculate_month_difference, get_config
from generic_tools import calculate_start_of_next_period, crb_number_months

config = get_config()

pd.options.mode.chained_assignment = None
con = config['constants']
static_period = crb_number_months()


class DownsellUpsell:
    def __init__(self):
        pass

    @time_function
    def crb_upsell_flags(self, df):
        """
        Function creates flags for upsold and downsold customers, and returns the original dataframe with these
        additional columns created.
        First months that have not been flagged in another bucket are identified, and ARR changes checked across the
        period. If the customer was existing at the start of the period, and ARR has increased or decreased in the
        period, then a flag is created. This period can either be static or variable, depending on the type of CRB. The
        static_period bool indicates which logical path it should take.

        :param df: The input dataframe. This must have been passed through previous functions, including the
        churn and new logo function and the cross-sell and downgrade function
        :return: df - the original dataframe with the additional flags created
        """
        # Create existing_customer and existing_product flags to support identification of upsell/downsell
        if static_period:
            dict = {}
            for x in range(con['month_period'], 100): # Set to 100 as mapping unlikely to be exhausted
                dict[x] = 1

            # Calculate flag for static snowball by setting flag as false in the initial period following a start date,
            # and true thereafter
            cust_start_diff = calculate_month_difference(df, 'customer_start_date', 'month')
            prod_start_diff = calculate_month_difference(df, 'product_start_date', 'month')

            df[f'existing_customer_flag'] = cust_start_diff.map(dict).fillna(0)
            df[f'existing_product_flag'] = prod_start_diff.map(dict).fillna(0)

        else:
            # Flags calculated by setting value to false prior to the end of a customer's first period, and value to
            # true afterwards
            df['start_of_next_period_customer'] = calculate_start_of_next_period(df, 'customer_start_date')
            df['start_of_next_period_product'] = calculate_start_of_next_period(df, 'product_start_date')

            cust_start_diff = calculate_month_difference(df, 'customer_start_date', 'month')
            prod_start_diff = calculate_month_difference(df, 'product_start_date', 'month')

            cust_next_period_diff = calculate_month_difference(df, 'customer_start_date',
                                                               'start_of_next_period_customer')
            prod_next_period_diff = calculate_month_difference(df, 'product_start_date',
                                                               'start_of_next_period_product')
            # Condition is that time must be longer than that to next period
            df[f'existing_customer_flag'] = np.where(cust_start_diff >= cust_next_period_diff, 1, 0)
            df[f'existing_product_flag'] = np.where(prod_start_diff >= prod_next_period_diff, 1, 0)

        # Create condition to check if any other snowball flags have been raised
        mask = ((df[f'new_customer_flag'] == 0) &
                (df[f'customer_churn_flag'] == 0) &
                (df[f'cross_sell_flag'] == 0) &
                (df[f'product_churn_flag'] == 0) &
                # Also ensure that customer existed in previous time period
                (df[f'existing_customer_flag'] == 1) &
                (df[f'existing_product_flag'] == 1))

        # Assign flags as value 1 where upsell/downsell conditions met
        print("Test 2", df.head())
        print("Test 3", df.index)
        upsell_bool = (df[f'arr_delta'] > 0) & mask
        downsell_bool = (df[f'arr_delta'] < 0) & mask
        print("Test 4", upsell_bool)
        print("Test 5", downsell_bool)
        df.loc[upsell_bool, f'upsell_flag'] = 1
        df.loc[downsell_bool, f'downsell_flag'] = 1

        # Fill in zeros for rows where upsell/downsell conditions not met
        df[f'upsell_flag'] = df[f'upsell_flag'].fillna(0)
        df[f'downsell_flag'] = df[f'downsell_flag'].fillna(0)

        return df