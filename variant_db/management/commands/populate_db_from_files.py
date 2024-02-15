import pandas as pd


def var_db_upload_controller(files: list[pd.DataFrame]) -> None:
    """
    The controller function which uploads a user-provided list of variant files
    into the relevant Eris tables.
    This is currently only called from the command line interface.

    :param: files - a list of Pandas DataFrames, each of which contains data from a single variant file
    """
    # TODO: write the real code!
    print("TEST")
    # for each dataframe, do any basic validation, and then put its data into the database tables
