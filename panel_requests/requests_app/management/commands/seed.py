#!usr/bin/env python

"""
Coordinates functions to:

    1. Pull in and parse data from...
        a. PanelApp API (via parse_pa.py)
        b. JSON file of parsed test directory data (via import_td_data)
        c. Request form excel file (via parse_form.py)

    2. Insert the parsed data into the database (via insert_panel.py or
    insert_ci.py)

Test directory data cannot be imported before the database has been
populated with all current PanelApp panels. This is because most
clinical indications in the test directory are linked to specific
panels.


Usage examples: Importing PanelApp data

- Import all current PanelApp panels
    python manage.py seed panelapp all

- Import the current version of a single PanelApp panel
    python manage.py seed panelapp <panel_id>

- Import a specific version of a single PanelApp panel
    python manage.py seed panelapp <panel_id> <panel_version>


Usage examples: Importing parsed test directory data

- Import data from a JSON file of parsed test directory data (current version)
    python manage.py seed test_dir <input_json> <Y/N>


Usage examples: Parsing and importing a request form

- Parse a panel request form and import data
    python manage.py seed form <input_file>

"""


import json

from . import parse_pa
from . import parse_form
from . import insert_panel
from . import insert_ci

from panelapp import queries

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Coordinate the functions in other scripts to import and " \
        "parse data, then use insert.py to insert the cleaned data into " \
        "the database."

    def __init__(self, *args, **kwargs):

        self.which = kwargs['which']
        self.test = kwargs['test']

        if self.which == 'panelapp':
            self.panel_id = kwargs['panel_id']
            self.panel_version = kwargs['panel_version']

        elif self.which == 'test_dir':
            self.input_json = kwargs['input_json']
            self.current = kwargs['current']

        elif self.which == 'form':
            self.input_file = kwargs['input_file']

    def add_arguments(self, parser):
        """ Define the source of the data to import. """

        subparsers = parser.add_subparsers()

        # subparser defining whether this is a test (so no database access)

        parser_test = subparsers.add_parser('test', help='Test the script')

        parser_test.add_argument(
            "test", type=bool, default=False, help="PanelApp panel id")

        parser_test.set_defaults(which='test')

        # subparser defining inputs for importing data from PanelApp

        parser_p = subparsers.add_parser('panelapp', help='Import panel data')

        parser_p.add_argument(
            "panel_id", type=str, help="PanelApp panel id",)

        parser_p.add_argument(
            "panel_version", type=str, nargs='?', default=None,
            help="PanelApp panel version (optional)",)

        parser_p.set_defaults(which='panelapp')

        # subparser defining inputs for importing data from TD

        parser_d = subparsers.add_parser('test_dir', help='Import TD data')

        parser_d.add_argument(
            'input_json', type=str,
            help="Path to JSON file of parsed TD data",)

        parser_d.add_argument(
            "current", type=str, choices=['Y', 'N'],
            help="Is this test directory the current version Y/N",)

        parser_d.set_defaults(which='test_dir')

        # subparser defining inputs for importing data from request form

        parser_f = subparsers.add_parser('form',
            help='Import request form data')

        parser_f.add_argument(
            "input_file", type=str,
            help="Path to request form file",)

        parser_f.set_defaults(which='form')

    def parse_single_pa_panel(self, panel_id, panel_version):
        """ Use parse_pa.py functions to import and parse data from a
        single PanelApp panel.

        args:
            panel_id [str]: PanelApp ID for a panel
            panel_version [str/None]: Optional to specify panel version

        returns:
            parsed_data [dict/None]: data to insert into db
        """

        parsed_data = None

        parser = parse_pa.PanelParser(
            panel_id=panel_id,
            panel_version=panel_version)

        # retrieve panel data from PanelApp

        panel_data = parser.get_panelapp_panel(panel_id, panel_version)

        # extract the required data for the panel and its genes and regions

        if panel_data:

            info_dict = parser.setup_output_dict(panel_data)
            info_dict = parser.parse_gene_info(panel_data, info_dict)
            parsed_data = parser.parse_region_info(panel_data, info_dict)

        else:
            print(f'Data could not be retrieved for panel {panel_id}.')

        return parsed_data

    def parse_all_pa_panels(self):
        """ Get a list of IDs for all current PanelApp panels, then
        parse and import all of these panels to the DB.

        returns:
            parsed_data [list of dicts]: data dicts for all panels
        """

        print('Parsing data for all PanelApp panels...')

        parsed_data = []

        # get a list of ids for all current PA panels

        all_panels = queries.get_all_panels()

        # retrieve and parse each panel

        for panel_id, panel_object in all_panels.items():

            panel_data = self.parse_single_pa_panel(panel_id, None)

            parsed_data.append(panel_data)

        print('Data parsing completed.')

        return parsed_data

    def parse_form_data(self, filepath):
        """ Use parse_form.py to import and parse data from a panel
        request form.

        args:
            filepath [str]: path to request form file

        returns:
            parsed_data [dict]: data to insert into db
        """

        print('Parsing request form...')

        parser = parse_form.FormParser(filepath=filepath)

        info, panel_df, gene_df, region_df = parser.get_form_data(filepath)

        ci = info['ci']
        req_date = info['req_date']

        info_dict = parser.setup_output_dict(ci, req_date)
        info_dict = parser.parse_genes(info_dict, gene_df)
        parsed_data = parser.parse_regions(info_dict, region_df)

        print('Form parsing completed.')

        return parsed_data

    def handle(self, *args, **kwargs):
        """ Coordinates functions to import and parse data from
        specified source, then calls inserter to insert cleaned data
        into the database. """

        process = self.which

        assert process, "Please specify data type: panels / test_dir / form"

        # import and parse PanelApp data (panel_version optional)

        if process == 'panelapp':

            # parse data from ALL current PanelApp panels

            if self.panel_id == 'all':
                parsed_data = self.parse_all_pa_panels()

            # parse data from a single PanelApp panel

            else:
                if self.panel_version:
                    panel_version = self.panel_version

                else:
                    panel_version = None

                parsed_data = [self.parse_single_pa_panel(
                    self.panel_id, panel_version)]

            # insert parsed data (list of panel dicts) into the db

            if not self.test:

                print('Importing panels into database...')

                for panel_dict in parsed_data:
                    if panel_dict:
                        insert_panel.insert_data(panel_dict)

                print('Done.')

            return parsed_data

        # import test directory data (td_json & td_current required)

        elif process == 'test_dir':

            with open(self.input_json) as reader:
                json_data = json.load(reader)

            if self.current == 'Y':
                current = True
            elif self.current == 'N':
                current = False

            if not self.test:
                new_panels = insert_ci.insert_data(json_data, current)

        # import and parse data from a request form (filepath required)

        elif process == 'form':

            # read in data from the form

            parsed_data = self.parse_form_data(self.input_file)

            ci = parsed_data['ci']
            date = parsed_data['req_date']
            source = f'request_{date}_{ci}'

            # insert new panel and update previous panel links

            if not self.test:
                new_panels = insert_panel.insert_data(parsed_data)

                insert_panel.update_ci_panel_links(
                    ci, source, date, new_panels)

            return parsed_data
