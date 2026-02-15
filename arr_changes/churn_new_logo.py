import pandas as pd
import numpy as np
from generic_tools import time_function, calculate_month_difference, get_config
from generic_tools import calculate_start_of_next_period, crb_number_months

config = get_config()

pd.options.mode.chained_assignment = None
con = config['constants']
static_period = crb_number_months()

class ChurnNewLogo:
    def __init__(self):
        pass

    @time_function
    def crb_add_churn_flags(self, df):
        """
        Function creates flags for churned and new customers, and returns the original dataframe with these added
        It looks for the start and end date of a customer, and flags a certain number of months after this depending
        on whether the CRB is a fixed number of months or a defined period. The static_period bool indicates which
        logical path it should take.

        :param df: The input dataframe. This must have been passed through previous function sand contains the 'month',
         customer_start_date' and 'customer_churn_date' columns
        :return: df - the original dataframe with the additional flags created
        """
        # If LXM snowball then choose this option
        if static_period:

            # Create dictionary to map in flags
            dict = {}
            for x in range(0, con['month_period']):
                dict[x] = 1

            # Calculate churn and new customer flags and map in values with dictionary
            for new_col_name, date_comparison_col in zip(['new_customer', 'customer_churn'],
                                                         ['customer_start_date', 'customer_churn_date']):
                time_diff = calculate_month_difference(df, date_comparison_col, 'month')
                df[f'{new_col_name}_flag'] = time_diff.map(dict).fillna(0)

        else:
            # Use calculate_month_difference function to work out eligible months and fill those with flags
            for new_col_name, date_comparison_col in zip(['new_customer', 'customer_churn'],
                                                         ['customer_start_date', 'customer_churn_date']):
                df['start_of_next_period'] = calculate_start_of_next_period(df, date_comparison_col)
                time_diff = calculate_month_difference(df, date_comparison_col, 'month',)
                print(time_diff)
                next_period_diff = calculate_month_difference(df, date_comparison_col, 'start_of_next_period')
                print(next_period_diff)
                df[f'{new_col_name}_flag'] = np.where((time_diff < next_period_diff) & (time_diff > 0),
                                                                      1,
                                                                      0)
            # Set boolean to prevent assigning the same row to new customer and cross sell
            not_new_or_churn = (df['new_customer_flag'] == 0) & \
                               (df['customer_churn_flag'] == 0)

            # Drop unnecessary columns
            df = df.drop(columns=['start_of_next_period'])
        return df