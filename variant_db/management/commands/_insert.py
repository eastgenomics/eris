#!/usr/bin/env python

from pandas import DataFrame
from django.db import transaction
from variant_db.models import *

def insert_stuff_into_db(workbook_df: DataFrame) -> None:
    """
    Function to import stuff into DB

    :param workbook_df: DataFrame instance of imported variant-data workbook 
    """
    pass