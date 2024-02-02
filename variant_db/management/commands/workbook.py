'''
Workbook utils
'''
#!/usr/bin/env python

import re
import pandas as pd
from typing import Tuple, List, Dict

def read_workbook(workbook_file: str) -> List[Dict[str, str|int]]:
    """
    Reads CSV workbook into a list of dicts, one per row.
    Column names are cleaned in the following ways for compatibility
    with the API:
    - strings to lowercase
    - whitespace trimmed and replaced with underscores
    - ACGS columns are renamed to their DB counterparts

    :param: workbook: path to workbook file
    """
    wb_df = pd.read_csv(workbook_file)
    wb_df.columns = [_clean_column_name(x) for x in wb_df.columns]
    validate_workbook(wb_df)
    pivoted_df = _pivot_df_as_row_dict(wb_df)
    pivoted_df = _add_panels_field(pivoted_df)
    return pivoted_df

def validate_workbook(workbook: pd.DataFrame) -> pd.DataFrame:
    """
    Validate workbook (TODO)

    :param: workbook: workbook dataframe
    """
    return workbook

def _pivot_df_as_row_dict(df: pd.DataFrame) -> List[Dict[str, str|int]]:
    """
    Convert DataFrame to list of rows, where each row is a dictionary
    """
    df_dict = df.to_dict()
    n_rows = range(df.shape[0])
    pivoted_df = [row_dict(df_dict, i) for i in n_rows]
    return pivoted_df

def _row_dict(df_dict: dict, i: int) -> Dict[str, str|int]:
    """
    Helper function to return a row dict given the row index
    """
    return {k: df_dict[k][i] for k in df_dict}

def _clean_column_name(column_header: str) -> str:
    """
    Helper function to clean the column name
    """
    for func in [_replace_with_underscores, _rename_acgs_column, _convert_name_to_lowercase]:
        column_header = func(column_header)
    
    return column_header

def _replace_with_underscores(column_header: str) -> str:
    """
    Replaces whitespace with an underscore (except fields ending with "ID")
    """
    if column_header.endswith("ID"):
        column_header = column_header.replace("ID", "_ID")
    return column_header.replace(" ", "_")

def _rename_acgs_column(column_header: str) -> str:
    """
    Add "_verdict" to the end of ACGS columns
    """
    if re.match("[BP][AMPSV][SV]?\d$", column_header):
        return column_header + "_verdict"
    else:
        return column_header

def _convert_name_to_lowercase(column_header: str, exclude: Tuple[str] = ("verdict", "evidence", "ACGS")) -> str:
    """
    Converts names to lowercase. Returns an unchanged string if it ends with anything in the `exclude` option
    """
    if column_header.endswith(exclude):
        return column_header
    else:
        return column_header.lower()

def _add_panels_field(pivoted_df: List[Dict]) -> List[Dict]:
    """
    Splits up the "panels" field into single panels (";"-separated), where each panel is a dict with `panel_name` and `panel_version`
    """
    for row in pivoted_df:
        row["panels"] = [_parse_panel(panel) for panel in row["panel"].split(";")]
    return pivoted_df

def _parse_panel(panel: str) -> Dict[str, str]:
    """
    Splits a single panel string into "name" and "version" components, returning a dict
    """
    split_panel = panel.split("_")
    return {"name": split_panel[0], "version": split_panel[-1]}
