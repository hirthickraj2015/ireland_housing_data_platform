import pandas as pd
import numpy as np
from generic_tools import time_function, calculate_month_difference, get_config
from generic_tools import calculate_start_of_next_period, crb_number_months

config = get_config()

pd.options.mode.chained_assignment = None
con = config['constants']
static_period = crb_number_months()


class DowngradeCrossSell:
    def __init__(self):
        pass

    @time_function
    def crb_add_cross_sell_flags(self, df):
        """
        Function creates flags for cross-sold and downgraded customers, and returns the original dataframe with these
        additional columns created
        It looks for the product start and end dates of a customer, and flags months if no flag has already been added
        for new logo or churn. The number of months it flags is determined by whether the CRB is a fixed number of
        months or a defined period. The static_period bool indicates which logical path it should take.

        :param df: The input dataframe. This must have been passed through previous functions, including the churn and
         new logo function and contain the 'month', customer_start_date' and 'customer_churn_date' columns
        :return: df - the original dataframe with the additional flags created
        """
        # Set boolean to prevent assigning the same row to new customer and cross sell
        not_new_or_churn = (df['new_customer_flag'] == 0) & \
                           (df['customer_churn_flag'] == 0)

        # If LXM snowball then choose this option
        if static_period:

            # Create dictionary to use for filling mapping
            dict = {}
            for x in range(0, con['month_period']):
                dict[x] = 1

            # Calculate product churn and cross sell flags
            for new_col_name, date_comparison_col in zip(['cross_sell', 'product_churn'],
                                                         ['product_start_date', 'product_churn_date']):
                time_diff = calculate_month_difference(df, date_comparison_col, 'month')
                df.loc[not_new_or_churn, f'{new_col_name}_flag'] = time_diff.map(dict)
                df[f'{new_col_name}_flag'] = df[f'{new_col_name}_flag'].fillna(0)

        else:

            # Use calculate_month_difference function to work out eligible months and fill those with flags
            for new_col_name, date_comparison_col in zip(['cross_sell', 'product_churn'],
                                                         ['product_start_date', 'product_churn_date']):
                df['start_of_next_period'] = calculate_start_of_next_period(df, date_comparison_col)
                time_diff = calculate_month_difference(df, date_comparison_col, 'month')
                next_period_diff = calculate_month_difference(df, date_comparison_col, 'start_of_next_period')

                df[f'{new_col_name}_flag'] = np.where(not_new_or_churn & (time_diff < next_period_diff) & (time_diff > 0),
                                                                      1,
                                                                      0)
                df[f'{new_col_name}_flag'] = df[f'{new_col_name}_flag'].fillna(0)

            # Drop unnecessary columns
            df = df.drop(columns=['start_of_next_period'])

        return df
