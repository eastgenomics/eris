#!usr/bin/env python

"""
Test suite for scripts in requests_app/management/commands which don't
interact with the database (i.e. the scripts which deal with parsing
data).

Files required for tests are provided in requests_app/testing_files.

PanelApp panel 90 (version 1.80) is used as a test panel because it is
the smallest panel which contains at least one each of genes, regions
and STRs.
"""


import json
import pandas as pd

from .management.commands import seed
from .management.commands import create_form
from .management.commands import parse_form
from .management.commands import functions_hgnc as hgnc


# Define paths to test files

dir = 'testing_files/'
hgnc_file = f'{dir}testing_hgnc_dump.txt'
parsed_panel = f'{dir}testing_parse_panel.json'

test_forms = {
    1: f'{dir}testing_input_form_1.xlsx',
    2: f'{dir}testing_input_form_2.xlsx',
    3: f'{dir}testing_input_form_3.xlsx'}

parsed_forms = {
    1: f'{dir}testing_parse_form_1.json',
    2: f'{dir}testing_parse_form_2.json',
    3: f'{dir}testing_parse_form_3.json'}


class TestHgnc:
    """ Tests for the functions in functions_hgnc.py.

    random_hgncs [list] contains 25 gene dicts with the form:
        {'hgnc': <hgnc ID>,
        'current': <current gene symbol>,
        'other': <randomly selected alternative symbol, if any exist>}
    """

    def test_hgnc_from_symbol(self):
        """ Tests get_hgnc_from_symbol using the current gene symbol for
        25 randomly selected HGNC IDs. """

        errors = []
        hgnc_df = hgnc.import_hgnc_dump(hgnc_file)
        hgnc_df = hgnc.rename_columns(hgnc_df)
        random_hgncs = hgnc.random_hgncs(hgnc_df)

        for ele in random_hgncs:

            result = hgnc.get_hgnc_from_symbol(hgnc_df, ele['row_current'])

            if result != ele['row_hgnc']:

                errors.append(f"DF row: {ele}\nFunction result: {result}")

        assert not errors, '\n'.join(errors)

    def test_symbol_from_hgnc(self):
        """ Tests get_symbol_from_hgnc using the HGNC ids of 25 randomly
        selected genes. """

        hgnc_df = hgnc.import_hgnc_dump(hgnc_file)
        hgnc_df = hgnc.rename_columns(hgnc_df)

        random_hgncs = hgnc.random_hgncs(hgnc_df)

        errors = []

        for ele in random_hgncs:

            result = hgnc.get_symbol_from_hgnc(hgnc_df, ele['row_hgnc'])

            if result != ele['row_current']:

                errors.append(f"{ele['row_hgnc']} returned {result}, "
                    f"not {ele['row_current']}")

        assert not errors, '\n'.join(errors)


class TestSeed:
    """ Tests for the functions in seed.py. The parse_all_pa_panels
    function isn't covered because it would mean storing a complete dump
    of panelapp, which would be Large.
    """

    def test_parse_single_panel(self):
        """ Tests parse_single_pa_panel from seed.py. This involves
        calling all four functions within parse_pa.py.

        testing_parse_panel.txt contains the json output of
        parse_single_pa_panel for PA panel 90 v1.80. """

        command = seed.Command(
            test=True, which='panelapp', panel_id='90', panel_version='1.80')

        result = command.handle()

        print(result)

        with open(parsed_panel, 'r') as reader:
            correct_output = json.load(reader)

        assert result == correct_output

    def test_parse_forms(self):
        """ Tests parse_form_data from seed.py. This involves
        calling all four functions within parse_pa.py. """

        errors = []

        for index, form in test_forms.items():

            parsed_form = parsed_forms[index]

            result = seed.Command(
                test=True, which='form', input_file=form).handle()

            with open(parsed_form, 'r') as reader:
                correct_output = json.load(reader)

            if result != correct_output:
                errors.append(f'Form {form} parsed incorrectly.')

        assert not errors, '\n'.join(errors)
