import pandas as pd
from .insert import *
from .workbook import read_workbook
from .insert import insert_row


def upload(workbook: str) -> None:
    """
    The controller function which uploads a user-provided list of variant files
    into the relevant Eris tables.
    This is currently only called from the command line interface.

    :param: files - a list of Pandas DataFrames, each of which contains data from a single variant file
    """
    # call eris.variant_db._insert functions here
    wb_df = read_workbook(workbook)
    for row in wb_df:
        insert_row(row)
