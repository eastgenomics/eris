#!usr/bin/env python

"""
Functions for dealing with data from a tab-delimited text file
('filename') containing a dump of the HGNC database.

Instructions for creating the text file can be found in the README.
"""


import pandas as pd
import random


def import_hgnc_dump(filename):
    """ Read in a tab-separated dump of the HGNC database and create a
    pandas dataframe from it.

    args:
        filename [path]: containing dump of HGNC database

    returns:
        hgnc_df [pandas dataframe]
    """

    hgnc_df = pd.read_csv(filename, sep='\t')

    return hgnc_df


def rename_columns(hgnc_df):
    """ Rename the columns of the hgnc dataframe to a standardised format.

    args:
        hgnc_df [pandas dataframe]: created from text file dump

    returns:
        hgnc_df [pandas dataframe]: with updated column names
    """

    renamed_columns = [
        'hgnc_id',
        'symbol',
        'prev_symbols',
        'alias_symbols']

    hgnc_df.columns = renamed_columns

    return hgnc_df


def get_hgnc_from_symbol(hgnc_df, gene_symbol):
    """ Get the HGNC ID for a supplied gene symbol, if one exists. A
    gene symbol may appear in the 'symbol', 'alias_symbol' or
    'prev_symbol' columns depending on whether it is current or not, so
    the function looks through all three in turn.

    args:
        hgnc_df: pandas df containing dump of HGNC site
        gene_symbol [str]: query gene symbol

    returns:
        hgnc_id [str], or None: HGNC ID of query gene
    """

    hgnc_id = None

    # if a row exists where this gene is the official gene symbol,
    # get that row's index and hgnc id

    try:

        target_index = hgnc_df.index[hgnc_df['symbol'] == gene_symbol]
        hgnc_id = hgnc_df.loc[target_index[0], 'hgnc_id']

    except IndexError:

        # or see if it's in the 'previous symbols' field

        try:
            i = 0

            for value in hgnc_df['alias_symbols']:
                if gene_symbol in str(value):

                    hgnc_id = hgnc_df.iloc[i].loc['hgnc_id']
                    break

                i += 1

        # or see if it's in the 'alias symbols' field

        except IndexError:

            j = 0

            for value in hgnc_df['prev_symbols']:
                if gene_symbol in str(value):

                    hgnc_id = hgnc_df.iloc[j].loc['hgnc_id']
                    break

                j += 1

    return hgnc_id


def get_symbol_from_hgnc(hgnc_df, hgnc_id):
    """ Get the current gene symbol associated with a supplied HGNC id,
    if one exists.

    args:
        hgnc_df: pandas df containing dump of HGNC site
        hgnc_id [str]: query HGNC id

    returns:
        gene_symbol [str], or None: current symbol of query gene
    """

    try:
        # if a row exists with this HGNC id, get the symbol for that row

        target_index = hgnc_df.index[hgnc_df['hgnc_id'] == hgnc_id]

        gene_symbol = hgnc_df.loc[target_index[0], 'symbol']

    except IndexError:

        gene_symbol = None

    return gene_symbol


def random_hgncs(hgnc_df):
    """ Given an HGNC dataframe, select 25 random genes to test with.

    returns:
        test_data [list]: 25 dicts with hgnc id, current symbol, and a
            randomly selected alternative symbol (if any exist)
    """

    test_data = []
    hgnc_df = hgnc_df.applymap(lambda x: str(x).strip())
    num_ids = len(hgnc_df.index)

    while len(test_data) < 25:

        # choose a random df row, store hgnc id and current symbol

        row = random.randint(1, num_ids)
        row_hgnc = hgnc_df.loc[row, 'hgnc_id']
        row_current = hgnc_df.loc[row, 'symbol']

        # list all previous/alias symbols in that row, pick one at random

        all_non_current = []
        prev = hgnc_df.loc[row, 'prev_symbols']
        alias = hgnc_df.loc[row, 'alias_symbols']

        for symbol_string in prev, alias:
            if symbol_string.lower() != 'nan':
                for ele in symbol_string.split(','):
                    all_non_current.append(ele.strip())

        if all_non_current:
            non_current = random.choice(all_non_current)

            # return the row's hgnc, current symbol, and previous symbol

            row_dict = {
                'row_hgnc': row_hgnc,
                'row_current': row_current,
                'row_previous': non_current}

            test_data.append(row_dict)

    return test_data
