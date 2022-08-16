#!usr/bin/env python

"""
Coordinates functions to:

    1. Pull in and parse data from...
        a. a genomic test directory file (via import_td_data)
        b. a request form (via parse_form.py)
        c. an unmodified PanelApp panel (via parse_pa.py)

    2. Insert the parsed data into the database (via insert.py)

Test directory data cannot be imported before the database has been
populated with all current PanelApp panels. This is because clinical
indications in the test directory are all linked to specific panels.

Usage:

    python manage.py seed <source> <options>

Options (*optional, defaults to None):

    source: 'd' (test directory), 'f' (request form), or 'p' (PanelApp)
    *--filepath [str]: Path to request form (required if source = f)
    *--panel_id [str]: PanelApp panel id (required if source = p)
    *--panel_version [str]: PanelApp panel version (optional if source = p)


Usage examples:

1. (PARTIALLY TESTED) Import parsed data from the current version of the test directory

    python manage.py seed d --td_json <filename> --td_current Y

2. (NOT WORKING YET) Import parsed data from a non-current version of the test directory

    python manage.py seed d --td_json <filename> --td_current N

3. (NOT WORKING YET) Parse a panel request form and import data

    python manage.py seed f --infile <filename>

4. (PARTIALLY TESTED) Parse and import a single PanelApp panel

    python manage.py seed p --panel_id <id> (--panel_version <version>)

5. (PARTIALLY TESTED) Parse and import all current PanelApp panels

    python manage.py seed p --panel_id all

"""


import json

from . import parse_pa as parse_pa
from . import parse_form as parse_form
from . import insert_panel as insert_panel
from . import insert_ci as insert_ci

from panelapp import queries

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Coordinate the functions in other scripts to import and \
        parse data, then use insert.py to insert the cleaned data into \
        the database."

    def add_arguments(self, parser):
        """ Define the source of the data to import. """

        # 'source' arg is always required, and has 3 valid values
        parser.add_argument(
            "source",
            nargs = 1,
            choices = ['d', 'f', 'p'],
            help = "Specify source of data to insert. Options: 'd' for test \
                directory, 'f' for request form, or 'p' for PanelApp.",)

        # '--td_json' is required if source = d
        parser.add_argument(
            "--td_json",
            nargs = '?',
            default = None,
            help = "Path to JSON file of TD data",)

        # '--td_current' is required if source = d, and has 2 valid values
        parser.add_argument(
            "--td_current",
            nargs = '?',
            default = None,
            choices = ['Y', 'N'],
            help = "Is this test directory the current version: Y/N",)

        # 'filepath' kwarg is required if source = f
        parser.add_argument(
            "--filepath",
            nargs = '?',
            default = None,
            help = "Path to request form file",)

        # 'panel_id' kwarg is required if source = p
        parser.add_argument(
            "--panel_id",
            nargs = '?',
            default = None,
            help = "PanelApp panel id",)

        # 'panel_version' kwarg is optional if source = p
        parser.add_argument(
            "--panel_version",
            nargs = '?',
            default = None,
            help = "PanelApp panel version (optional)",)


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

        data = parse_pa.Data(
            panel_id = panel_id,
            panel_version = panel_version)

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

        # source must be specified

        if kwargs['source']:

            source = kwargs['source'][0]


            ## import and parse PanelApp data (panel_id required)

            if (source == 'p') and (kwargs['panel_id']):

                panel_id = kwargs['panel_id']

                # parse data from all current PanelApp panels

                if panel_id == 'all':

                    parsed_data = self.parse_all_pa_panels()

                # parse data from a single PanelApp panel

                else:
                    if kwargs['panel_version']:
                        panel_version = kwargs['panel_version']

                    else:
                        panel_version = None

                    parsed_data = [self.parse_single_pa_panel(
                        panel_id,
                        panel_version)]

                # insert parsed data (list of panel dicts) into the db

                for panel_dict in parsed_data:
                    if panel_dict:

                        insert_panel.insert_data(panel_dict)


            ## import and parse data from a request form (filepath required)

            elif (source == 'f') and (kwargs['filepath']):

                filepath = kwargs['filepath']

                # parsed_data = self.parse_form_data(filepath)

                print("The app can't deal with request forms yet.")


            ## import test directory data (td_json & td_current required)

            elif (source == 'd') and \
                (kwargs['td_json']) and \
                (kwargs['td_current']):

                td_json = kwargs['td_json']
                td_current = kwargs['td_current']

                path = f'requests_app/management/commands/{td_json}'

                with open(path) as reader:
                    json_data = json.load(reader)

                if td_current == 'Y':
                    current_td = True

                elif td_current == 'N':
                    current_td = False

                insert_ci.insert_data(json_data, current_td)


            ## a valid combination of arguments is required

            else:
                print(f'Error reading in arguments. \
                    \nSpecified source: {source} \
                    \nSupplied args: {args} \
                    \nSupplied kwargs: {kwargs}')

        else:
            print("Data source must be specified. Options are d for test \
                directory, f for request form, or p for PanelApp.")
