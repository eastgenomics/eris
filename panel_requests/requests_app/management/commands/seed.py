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

    python manage.py seed panels all

- Import the current version of a single PanelApp panel

    python manage.py seed panels <panel_id>

- Import a specific version of a single PanelApp panel

    python manage.py seed panels <panel_id> <panel_version>


Usage examples: Importing test directory data

- Import data from a JSON file of parsed test directory data
- (Y/N specifies whether this is the current TD version)

    python manage.py seed test_dir <input_json> <Y/N>


Usage examples: Importing test directory data

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

    def add_arguments(self, parser):
        """ Define the source of the data to import. """

        subparsers = parser.add_subparsers()

        # subparser defining inputs for importing data from PanelApp

        parser_p = subparsers.add_parser('panels', help='Import panel data')

        parser_p.add_argument(
            "panel_id", type=str, help="PanelApp panel id",)

        parser_p.add_argument(
            "panel_version", type=str, nargs='?', default=None,
            help="PanelApp panel version (optional)",)

        parser_p.set_defaults(which='panels')

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

        data = parse_pa.PanelParser(
            panel_id=panel_id,
            panel_version=panel_version)

        # retrieve panel data from PanelApp

        panel_data = data.get_panelapp_panel(panel_id, panel_version)

        # extract the required data for the panel and its genes and regions

        if panel_data:

            info_dict = data.setup_output_dict(panel_data)
            info_dict = data.parse_gene_info(panel_data, info_dict)
            parsed_data = data.parse_region_info(panel_data, info_dict)

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

        # data = parse_form.Data(filepath)
        # request_data = data.get_form_data(filepath)
        # info_dict = data.setup_output_dict(request_data)
        # ...
        # return parsed_data

        """ parse_form.py hasn't been written yet. """

    def handle(self, *args, **kwargs):
        """ Coordinates functions to import and parse data from
        specified source, then calls inserter to insert cleaned data
        into the database. """

        process = kwargs['which']

        assert process, "Please specify data type: panels / test_dir / form"

        # import and parse PanelApp data (panel_version optional)

        if process == 'panels':
            panel_id = kwargs['panel_id']

            # parse data from ALL current PanelApp panels

            if panel_id == 'all':
                parsed_data = self.parse_all_pa_panels()

            # parse data from a single PanelApp panel

            else:
                if kwargs['panel_version']:
                    panel_version = kwargs['panel_version']

                else:
                    panel_version = None

                parsed_data = [self.parse_single_pa_panel(
                    panel_id, panel_version)]

            # insert parsed data (list of panel dicts) into the db

            for panel_dict in parsed_data:
                if panel_dict:
                    insert_panel.insert_data(panel_dict)

        # import test directory data (td_json & td_current required)

        elif process == 'test_dir':

            td_json = kwargs['input_json']
            td_current = kwargs['current']

            with open(td_json) as reader:
                json_data = json.load(reader)

            if td_current == 'Y':
                current = True
            elif td_current == 'N':
                current = False

            insert_ci.insert_data(json_data, current)

        # import and parse data from a request form (filepath required)

        elif process == 'form':
            filepath = kwargs['input_file']

            # parsed_data = self.parse_form_data(filepath)

            print("The app can't deal with request forms yet.")
