import pandas as pd
import numpy as np
import time
from tableauhyperapi import Connection, CreateMode, HyperProcess, Telemetry, TableDefinition, Inserter, SqlType, \
    TableName
import yaml

def get_config():
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    return config

con = get_config()['constants']

def time_function(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Function '{func.__name__}' took {execution_time:.6f} seconds to execute.")
        return result

    return wrapper


def get_sql_type(dtype):
    """
    Maps Pandas dtype to Tableau Hyper SQL type.

    Parameters:
        dtype (numpy.dtype): The Pandas data type of a column.

    Returns:
        SqlType: The corresponding Tableau Hyper SQL type.
    """
    if np.issubdtype(dtype, np.integer):
        return SqlType.int()
    elif np.issubdtype(dtype, np.floating):
        return SqlType.double()
    elif np.issubdtype(dtype, np.bool_):
        return SqlType.bool()
    elif np.issubdtype(dtype, np.datetime64):
        return SqlType.date()
    else:
        return SqlType.text()


def write_dataframe_to_hyper(df, output_loc):
    """
    Writes a dataframe to a Tableau Hyper file.

    Parameters:
        df (pandas.DataFrame): The dataframe to be written to the Hyper file.
        output_loc (str): The path to the output directory where the Hyper file will be saved and the name of the file,
          should end in .hyper

    Returns:
        None
    """
    # Define the Tableau Hyper file path
    hyper_file_path = output_loc

    # Connect to the Hyper process
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        # Create a new Hyper file
        with Connection(endpoint=hyper.endpoint, database=hyper_file_path, create_mode=CreateMode.CREATE) as connection:
            # Define the table schema dynamically based on dataframe columns
            columns = []
            for column in df.columns:
                dtype = df[column].dtype
                sql_type = get_sql_type(dtype)
                columns.append(TableDefinition.Column(column, sql_type))

            table_definition = TableDefinition(
                table_name=TableName("Extract", "Extract"),
                columns=columns
            )

            # Create the table in the Hyper file
            connection.catalog.create_table(table_definition)

            # Insert the dataframe data into the table
            with Inserter(connection, table_definition) as inserter:
                for _, row in df.iterrows():
                    values = [row[column] for column in df.columns]
                    inserter.add_row(values)

                inserter.execute()

    print(f"Dataframe successfully written to {hyper_file_path}")


def calculate_month_difference(df, start_date, end_date):

    # Calculate the difference in years and months
    new_col = (df[end_date].dt.year - df[start_date].dt.year) * 12 + df[end_date].dt.month - df[start_date].dt.month

    return new_col


def calculate_start_of_next_period(df, time_col):
    """

    :param month_num:
    :param crb_type:
    :return: df:
    """
    df['month_month'] = df[time_col].dt.month
    df['month_year'] = df[time_col].dt.year

    # Path if selected CRB is YTD or FYTD
    if con['crb_type'] in ['YTD', 'FYTD']:
        # If YTD, month_num will be preselected to be 1
        if con['crb_type'] == 'YTD':
            con['fy_start_month'] = 1
        df['month_next_period'] = con['fy_start_month']
        df.loc[df['month_month'] < con['fy_start_month'], 'year_next_period'] = df['month_year']
        df.loc[df['month_month'] >= con['fy_start_month'], 'year_next_period'] = df['month_year'] + 1
        # Set start of next year
        start_of_next_period = pd.to_datetime(dict(year=df['year_next_period'],
                                                   month=df['month_next_period'],
                                                   day=1))
        # df = df.drop(columns=['month_month', 'month_year', 'month_next_period', 'year_next_period'])

    # Path if selected CRB is QTD or FQTD
    elif con['crb_type'] in ['QTD', 'FQTD']:
        # If QTD, month_num will be preselected to be 1
        if con['crb_type'] == 'QTD':
            con['fy_start_month'] = 1
        # Run through four loops for each quarter, finding start of quarter and start of following quarter
        for x in range(0, 4):
            soq = (con['fy_start_month'] + 3 * x) % 12
            eoq = (con['fy_start_month'] + 3 * (x + 1)) % 12
            # Set zeros as twelves to represent December
            if soq == 0:
                soq = 12
            if eoq == 0:
                eoq = 12
            # Set next quarter month for all quarters that won't move into following year
            df.loc[(df['month_month'] >= soq) &
                   (df['month_month'] < 10) &
                   (df['month_month'] < eoq), 'month_next_period'] = eoq
            df.loc[(df['month_month'] >= soq) &
                   (df['month_month'] < 10) &
                   (df['month_month'] < eoq), 'year_next_period'] = df['month_year']
            # Set next quarter month for those that will move into following year
            df.loc[(df['month_month'] >= soq) &
                   (soq >= 10), 'month_next_period'] = eoq
            df.loc[(df['month_month'] >= soq) &
                   (soq >= 10), 'year_next_period'] = df['month_year'] + 1
        # Set start of next quarter
        start_of_next_period = pd.to_datetime(dict(year=df['year_next_period'],
                                                   month=df['month_next_period'],
                                                   day=1))
        # df = df.drop(columns=['month_month', 'month_year', 'month_next_period', 'year_next_period'])

    else:
        start_of_next_period = df[time_col] + pd.DateOffset(months=con['month_period'])

    return start_of_next_period


def calculate_start_of_current_period(df, time_col='month'):
    """
    Function for calculating the start of the current period. This is only applicable for YTD, FYTD, QTD and FQTD CRBs,
    and only appears in those paths. The start of the current period is used for calculating BoP revenue in these CRBs

    :param df: The name of the input dataframe to the function - must have a row for each month with ARR attached
    :param time_col: The string that is the name of the datetime column, default setting is month
    :return: start_of_next_period - pd.Series giving the start of chosen period (either Year, Quarter, FY or FQ)
    """
    df['month_month'] = df[time_col].dt.month
    df['month_year'] = df[time_col].dt.year

    # Path if selected CRB is YTD or FYTD
    if con['crb_type'] in ['YTD', 'FYTD']:
        # If YTD, month_num will be preselected to be 1
        if con['crb_type'] == 'YTD':
            con['fy_start_month'] = 1
        df['month_current_period'] = con['fy_start_month']
        df.loc[df['month_month'] < con['fy_start_month'], 'year_next_period'] = df['month_year'] - 1
        df.loc[df['month_month'] >= con['fy_start_month'], 'year_next_period'] = df['month_year']
        # Set start of next year
        start_of_next_period = pd.to_datetime(dict(year=df['year_next_period'],
                                                   month=df['month_next_period'],
                                                   day=1))

    # Path if selected CRB is QTD or FQTD
    elif con['crb_type'] in ['QTD', 'FQTD']:
        # If QTD, month_num will be preselected to be 1
        if con['crb_type'] == 'QTD':
            con['fy_start_month'] = 1
        # Run through four loops for each quarter, finding start of quarter and start of following quarter
        for x in range(0, 4):
            soq = (con['fy_start_month'] + 3 * x) % 12
            eoq = (con['fy_start_month'] + 3 * (x + 1)) % 12
            # Set zeros as twelves to represent December
            if soq == 0:
                soq = 12
            if eoq == 0:
                eoq = 12
            # Set next quarter month for all quarters that won't move into following year
            df.loc[(df['month_month'] >= soq) &
                   (df['month_month'] < 10) &
                   (df['month_month'] < eoq), 'month_next_period'] = soq
            df.loc[(df['month_month'] >= soq) &
                   (df['month_month'] < 10) &
                   (df['month_month'] < eoq), 'year_next_period'] = df['month_year']
            # Set next quarter month for those that will move into following year
            df.loc[(df['month_month'] >= soq) &
                   (soq >= 10), 'month_next_period'] = soq
            df.loc[(df['month_month'] >= soq) &
                   (soq >= 10), 'year_next_period'] = df['month_year'] - 1
        # Set start of next quarter
        start_of_next_period = pd.to_datetime(dict(year=df['year_next_period'],
                                                   month=df['month_next_period'],
                                                   day=1))

    return start_of_next_period


def encoder(df, col_for_encoding):
    """

    :param df: input dataframe containing unencoded column
    :param col_for_encoding: string name of the column to be encoded
    :return: df: original dataframe with original column replaced by encoded column
    """
    unique_values = np.unique(df[col_for_encoding])
    # encoded_values = map(lambda x: hashlib.md5(x.encode('utf-8')).hexdigest(), unique_values)
    encoded_values = pd.factorize(unique_values)[0]
    val_map = dict(zip(unique_values, encoded_values))
    df[col_for_encoding] = df[col_for_encoding].map(val_map)

    return df

def crb_number_months():
    if con['crb_type'] in ['number_of_months']:
        return True
    else:
        return False