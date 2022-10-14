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
from .management.commands import functions_hgnc as hgnc


hgnc_file = 'testing_files/testing_hgnc_dump.txt'
parsed_panel = 'testing_files/testing_parse_panel.json'
input_form_1 = 'testing_files/testing_input_form_1.xlsx'
parsed_form_1 = 'testing_files/testing_parse_form_1.json'
input_form_2 = 'testing_files/testing_input_form_2.xlsx'
parsed_form_2 = 'testing_files/testing_parse_form_2.json'
input_form_3 = 'testing_files/testing_input_form_3.xlsx'
parsed_form_3 = 'testing_files/testing_parse_form_3.json'


# handle() can return things as strings using the following syntax:
# self.stdout.write('whatever you want to return')

# you can test this using:

#from io import StringIO
# from django.core.management import call_command
# from django.test import TestCase

# class ClosepollTest(TestCase):
#     def test_command_output(self):
#         out = StringIO()
#         call_command('closepoll', stdout=out)
#         self.assertIn('Expected output', out.getvalue())


class TestHgnc:
    """ Tests for the functions in functions_hgnc.py.

    random_hgncs [list] contains 25 gene dicts with the form:
        {'hgnc': <hgnc ID>,
        'current': <current gene symbol>,
        'other': <randomly selected alternative symbol, if any exist>}
    """

    def test_hgnc_from_symbol():
        """ Tests get_hgnc_from_symbol, using both the current gene
        symbol and an alternative symbol for 25 randomly selected HGNC
        IDs. """

        hgnc_df = hgnc.import_hgnc_dump(hgnc_file)
        hgnc_df = hgnc.rename_columns(hgnc_df)

        random_hgncs = hgnc.random_hgncs(hgnc_df)

        errors = []

        for ele in random_hgncs:
            for symbol in 'current', 'other':

                result = hgnc.get_hgnc_from_symbol(hgnc_df, ele[symbol])

                if result != ele['hgnc']:

                    errors.append(
                        f'{ele[symbol]} returned {result}, not {ele["hgnc"]}')

        assert not errors, '\n'.join(errors)

    def test_symbol_from_hgnc():
        """ Tests get_symbol_from_hgnc using the HGNC ids of 25 randomly
        selected genes. """

        hgnc_df = hgnc.import_hgnc_dump(hgnc_file)
        hgnc_df = hgnc.rename_columns(hgnc_df)

        random_hgncs = hgnc.random_hgncs(hgnc_df)

        errors = []

        for ele in random_hgncs:

            result = hgnc.get_symbol_from_hgnc(hgnc_df, ele['hgnc'])

            if result != ele['current']:

                errors.append(
                    f"{ele['hgnc']} returned {result}, not {ele['current']}")

        assert not errors, '\n'.join(errors)


class TestSeed:
    """ Tests for the functions in seed.py. Functions not covered:
    - add_arguments
    - parse_all_pa_panels (hard to test as site is continuously updated)
    - handle
    """

    def test_parse_single_panel():
        """ Tests parse_single_pa_panel from seed.py. This involves
        calling all four functions within parse_pa.py.

        testing_parse_panel.txt contains the json output of
        parse_single_pa_panel for PA panel 90 v1.80. """

        result = seed.Command(
            which='panelapp', panel_id='90', panel_version='1.80').handle()

        with open(parsed_panel, 'r') as reader:
            correct_output = json.load(reader)

        assert result == correct_output

    def test_parse_forms():
        """ Tests parse_form_data from seed.py.This involves calling all
        four functions within parse_form.py.

        testing_parse_form_1.json contains the output of parse_form_data
        for testing_input_form_1.xlsx, which is the request form
        generated for CI R149.1. """

        errors = []

        files = {
            input_form_1: parsed_form_1,
            input_form_2: parsed_form_2,
            input_form_3: parsed_form_3}

        for input_form, parsed_form in files.items():

            result = seed.Command(which='form', input_file=input_form).handle()

            with open(parsed_form, 'r') as reader:
                correct_output = json.load(reader)

            if result != correct_output:
                errors.append(f'Form {input_form} parsed incorrectly.')

        assert not errors, '\n'.join(errors)


class TestForm:
    def test_form_creation():
        """ Tests for functions in create_form.py. Doesn't cover
        write_blank_form, write_data or format_excel. """

        errors = []

        results = create_form.Command(
            req_date='20221012', requester='JJM',
            ci_code='R149.1', hgnc_dump=hgnc_file).handle()

        file = 'request_form_20221012_R149.1_JJM.xlsx'

        headers = {
            'general': 1, 'panel': 6, 'gene': 9, 'region': 38, 'final': 46}

        generic_df = pd.DataFrame({
            'fields': [
                'Request date',
                'Requested by',
                'Clinical indication',
                'Form generated'],
            'data': [
                '20221012',
                'JJM',
                'R149.1',
                '2022-10-12 15:43:36.788535']}).set_index('fields')

        panel_df =

        gene_df =

        region_df =

        if results[0] != file:
            errors.append(f'Incorrect filename: {results[0]}')

        if results[1] != headers:
            errors.append(f'Incorrect row headers: {results[1]}')

        if results[2] != generic_df:
            errors.append(f'Incorrect generic df: {results[2]}')

        if results[3] != panel_df:
            errors.append(f'Incorrect panels df: {results[3]}')

        if results[4] != gene_df:
            errors.append(f'Incorrect gene df: {results[4]}')

        if results[5] != region_df:
            errors.append(f'Incorrect regions df: {results[5]}')

        assert not errors, '\n'.join(errors)
