import pandas as pd
from ._insert import *

def upload(workbook: str) -> None:
    """
    The controller function which uploads a user-provided list of variant files
    into the relevant Eris tables.
    This is currently only called from the command line interface.

    :param: files - a list of Pandas DataFrames, each of which contains data from a single variant file
    """
    # call eris.variant_db._insert functions here
    wb_df = pd.read_csv(workbook)
    _validate_workbook(workbook)
    print(wb_df)
    return wb_df


def _validate_workbook(workbook: pd.DataFrame):
    """
    Validate workbook

    :param: workbook - workbook dataframe
    """
    pass