'''
Workbook utils
'''
#!/usr/bin/env python

import re
import pandas as pd
from typing import Tuple, List

from .utils import enumerate_chromosome

def read_workbook(workbook: str) -> List[dict(str, str|int)]:
    """
    read workbook

    :param: workbook - path to workbook
    """
    wb_df = pd.read_csv(workbook)
    wb_df.columns = [clean_column_name(x) for x in wb_df.columns]
    _validate_workbook(wb_df)
    wb_df.numeric_chrom = enumerate_chromosome(wb_df.CHROM)
    pivoted_df = pivot_df_as_row_dict(wb_df)
    return pivoted_df

def _validate_workbook(workbook: pd.DataFrame):
    """
    Validate workbook

    :param: workbook - workbook dataframe
    """
    pass

def pivot_df_as_row_dict(df: pd.DataFrame):
    """
    Convert DataFrame to list of rows, where each row is a dictionary
    """
    df_dict = df.to_dict()
    n_rows = range(df.shape[0])
    pivoted_df = [_row_dict(df_dict, i) for i in n_rows]
    return pivoted_df

def _row_dict(df_dict: dict, i: int):
    """
    Helper function to return a row dict given the row index
    """
    return {k: df_dict[k][i] for k in df_dict}

def clean_column_name(column_header: str) -> str:
    """
    docs
    """
    for func in [_replace_with_underscores, _rename_hgvs_column, _convert_name_to_lowercase]:
        column_header = func(column_header)
    
    return column_header

def _replace_with_underscores(column_header: str) -> str:
    if column_header.endswith("ID"):
        column_header = column_header.replace("ID", "_ID")
    return column_header.replace(" ", "_")

def _rename_hgvs_column(column_header: str) -> str:
    if re.match("[BP][AMPSV][SV]?\d$", column_header):
        return column_header + "_verdict"
    else:
        return column_header

def _convert_name_to_lowercase(column_header: str, exclude: Tuple[str] = ("verdict", "evidence", "HGVS")) -> str:
    if column_header.endswith(exclude):
        return column_header
    else:
        return column_header.lower()