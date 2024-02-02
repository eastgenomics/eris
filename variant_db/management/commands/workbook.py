'''
Workbook utils
'''
#!/usr/bin/env python

import re
import pandas as pd
from typing import Tuple, List, Dict

from .utils import enumerate_chromosome

def read_workbook(workbook: str) -> List[Dict[str, str|int]]:
    """
    read workbook

    :param: workbook - path to workbook
    """
    wb_df = pd.read_csv(workbook)
    wb_df.columns = [clean_column_name(x) for x in wb_df.columns]
    validate_workbook(wb_df)
    pivoted_df = pivot_df_as_row_dict(wb_df)
    pivoted_df = add_panels_field(pivoted_df)
    return pivoted_df

def validate_workbook(workbook: pd.DataFrame):
    """
    Validate workbook

    :param: workbook - workbook dataframe
    """
    return workbook

def pivot_df_as_row_dict(df: pd.DataFrame):
    """
    Convert DataFrame to list of rows, where each row is a dictionary
    """
    df_dict = df.to_dict()
    n_rows = range(df.shape[0])
    pivoted_df = [row_dict(df_dict, i) for i in n_rows]
    return pivoted_df

def row_dict(df_dict: dict, i: int):
    """
    Helper function to return a row dict given the row index
    """
    return {k: df_dict[k][i] for k in df_dict}

def clean_column_name(column_header: str) -> str:
    """
    
    """
    for func in [replace_with_underscores, rename_hgvs_column, convert_name_to_lowercase]:
        column_header = func(column_header)
    
    return column_header

def replace_with_underscores(column_header: str) -> str:
    if column_header.endswith("ID"):
        column_header = column_header.replace("ID", "_ID")
    return column_header.replace(" ", "_")

def rename_hgvs_column(column_header: str) -> str:
    if re.match("[BP][AMPSV][SV]?\d$", column_header):
        return column_header + "_verdict"
    else:
        return column_header

def convert_name_to_lowercase(column_header: str, exclude: Tuple[str] = ("verdict", "evidence", "HGVS")) -> str:
    if column_header.endswith(exclude):
        return column_header
    else:
        return column_header.lower()

def add_panels_field(pivoted_df: List[Dict]) -> List[Dict]:
    for row in pivoted_df:
        row["panels"] = [parse_panel(panel) for panel in row["panel"].split(";")]
    return pivoted_df

def parse_panel(panel: str) -> Dict[str, str]:
    split_panel = panel.split("_")
    return {"name": split_panel[0], "version": split_panel[-1]}