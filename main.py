import os
import time
import pandas as pd
from generic_tools import get_config
import data_pre_checks
import data_pre_processing
import crb_checks
import crb_functions
from arr_changes import churn_new_logo, downgrade_cross_sell, downsell_upsell

# Set option to view full outputs in print mode
pd.set_option('display.max_columns', None)

start_time = time.time()
### ---------Initial script setup--------------------

# Initialise config requirements
config = get_config()

# Initialise the class and create an instance
pre_checks = data_pre_checks.DataPreChecks()
pre_processing = data_pre_processing.DataPreProcessing()
crb_checks = crb_checks.CustomerRevenueBridgeChecks()
crb = crb_functions.CustomerRevenueBridgeImplementation()

churn_new = churn_new_logo.ChurnNewLogo()
downgrade_cross = downgrade_cross_sell.DowngradeCrossSell()
downsell_upsell = downsell_upsell.DownsellUpsell()

## Set filepaths and locations
# @TODO: add file path & sharepoint easy link
root = os.path.dirname(os.getcwd())
path_in = root + config['file_locations']['path_in']
waterfall_path_out = root + config['file_locations']['waterfall_path_out']
flat_path_out = root + config['file_locations']['flat_path_out']

print(path_in)

### ---------Customer revenue bridge initial checks--------------------

## Read data
data = pd.read_csv(path_in, encoding='utf-8')
print(f"Data is loaded with columns \n {data.columns.tolist()}\n"
      f"and shape {data.shape}.")
data = data.rename(columns=config['column_headers']['initial_mapping'])

## Check config file has been implemented properly
crb_checks.check_config_time_period()

## Check presence of required columns
pre_checks.check_columns_presence(data)

## Check date and revenue column types
pre_checks.check_arr_column(data)
data = pre_checks.process_month_column(data, 'month', 'UK')

## Create primary key for rows
primary_key_columns = config['column_headers']['primary_key_columns']
df_primary = crb.create_primary_key(data, primary_key_columns)

## Check primary key uniqueness
non_unique_keys = crb_checks.check_primary_key_uniqueness(df_primary)

## Drop dimension columns and create dimension table
df_primary, df_dim = crb.drop_dimensions_columns(df_primary)

## Confirm that every customer has a month for every valid month
# df_month = pre_checks.check_month_completeness(df_primary)
df_month = pre_processing.fill_month_completeness(df_primary)

### ---------Customer revenue bridge calculations--------------------

## Remove non-recurring rows
df_month = crb.remove_non_recurring_rows(df_month)

## Calculate Customer/Product/Segment start/end dates
df_month = crb.calculate_segment_start_end_dates(df_month)
## Trim dataset to remove unnecessary rows
df_month = crb.trim_dataset(df_month)

## Calculate ARR change flags
df_month = crb.calculate_arr_changes(df_month)

### ---------ARR Movement flag and delta calculations--------------------
## Calculate churn, new logo, cross sell and product churn flags
df_month = churn_new.crb_add_churn_flags(df_month)
#df_month_test = df_month[np.logical_and(np.logical_and(df_month['customer_id']==1102, df_month['month']<='2018-06-01'), df_month['product_id']=='Paye Logiciel')]

## Calculate cross-sell and downgrade flags
df_month = downgrade_cross.crb_add_cross_sell_flags(df_month)

## Calculate upsell and downsell flags
df_month = downsell_upsell.crb_upsell_flags(df_month)

## Perform final calculations on dataset
df_month = crb.create_arr_deltas(df_month)

### ---------Output creation--------------------
## Create columns for output and join dimensions back on
df_flat_file = crb.create_flattened_output(df_month, df_dim)

## Melt into waterfall input shape
df_waterfall_file = crb.create_waterfall_output(df_flat_file)

df_flat_file.to_csv(flat_path_out, encoding='utf-8')

### ---------Perform CRB checks--------------------

## Check that no positive churn or product churn in dataset
crb_checks.check_no_positive_churn(df_flat_file)

## Check that no negative new logo or cross-sell
crb_checks.check_no_negative_new_logo(df_flat_file)

## Check that upsell and downsell has correct directionality
crb_checks.check_upsell_downsell_direction(df_flat_file)

## Check that waterfalls sum individually and for each customer
crb_checks.check_waterfall_sums(df_primary, df_waterfall_file)

### ---------Writing data to output--------------------

## Write data to file locations
df_waterfall_file.to_csv(waterfall_path_out, encoding='utf-8')
# df_waterfall.to_csv(waterfall_path_out)
# write_dataframe_to_hyper(df_waterfall)

print("--- %s seconds ---" % (time.time() - start_time))