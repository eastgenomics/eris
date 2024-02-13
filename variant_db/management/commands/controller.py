import logging
import pandas as pd
from django.db import transaction
from .insert import *
from .workbook import read_workbook
from .insert import insert_row

@transaction.atomic
def upload(workbook: str) -> None:
    """
    The controller function which uploads a user-provided variant workbook
    into the relevant Eris tables.
    This is currently only called from the command line interface.

    :param: workbook - a filepath to a workbook file represented as a string
    """
    # call eris.variant_db._insert functions here
    wb_df = read_workbook(workbook)
    for index, row in enumerate(wb_df):
        logging.info(f"Attempting to insert row {index}")
        insert_row(row)
