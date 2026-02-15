import pandas as pd
import numpy as np
import dask.dataframe as dd
from generic_tools import time_function, write_dataframe_to_hyper, calculate_month_difference, encoder
from generic_tools import calculate_start_of_current_period, calculate_start_of_next_period
from config import ColumnHeaders, Constants
from datetime import date
import hashlib
import numbers

pd.options.mode.chained_assignment = None
col_head = ColumnHeaders()
con = Constants()
column_suffix = column_suffix()
static_period = crb_number_months()

class IntChurnWinBack:
    def __init__(self):
        pass

    @time_function
    def int_churn_flags(df, customer_id_col, product_id_col, month_col, revenue_col):
        """
         Logic for win-back / intermittent churn:
         Aggregate revenue to the customer/product level. If a customer has 0 revenue across all products for a 12 month period
         they are considered to have intermittently churned at the start of that period and been won-back when there next
         non-zero revenue occurs

        """

        customer_prod = df.groupby([customer_id_col, product_id_col, month_col], as_index=False).agg({revenue_col: 'sum'})

        # TODO: complete this function

        return df