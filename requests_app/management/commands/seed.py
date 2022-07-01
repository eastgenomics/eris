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

    source: data source, can be 'd' (test directory), 'f' (request form), or 'p' (PanelApp)
    *--filepath [str]: Path to request form (required if source = f)
    *--panel_id [str]: PanelApp panel id (required if source = p)
    *--panel_version [str]: PanelApp panel version (optional if source = p)


Usage examples:

1. (NOT WORKING YET) Import parsed data from the current version of the test directory

    python manage.py seed d --td_source <version name> --td_current Y

2. (NOT WORKING YET) Import parsed data from a non-current version of the test directory

    python manage.py seed d --td_source <version name> --td_current N

3. (NOT WORKING YET) Parse a panel request form and import data

    python manage.py seed f --infile <path to form>

4. (NOT TESTED) Parse and import the current version of a single unmodified PanelApp panel

    python manage.py seed p --panel_id <id>

5. (NOT TESTED) Parse and import a previous version of a single unmodified PanelApp panel

    python manage.py seed p --panel_id <id> --panel_version <version>

"""


from django.core.management.base import BaseCommand
import requests_app.management.commands.parse_pa as parse_pa
import requests_app.management.commands.parse_form as parse_form
import requests_app.management.commands.insert as inserter


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

        # '--td_source' is required if source = d
        parser.add_argument(
            "--td_source",
            nargs = '?',
            default = None,
            help = "Test directory title including version",)

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


    def import_td_data(self, td_source, td_current):
        """ Import test directory data from <YUJIN'S SCRIPT> """

        # ...
        # return parsed_data

        """ this function needs to import the output of Yujin's script
        so it can be fed to the inserter """


    def parse_form_data(self, filepath):
        """ Use parse_form.py to import and clean request form data """

        # data = parse_form.Data(filepath)
        # request_data = data.get_form_data(filepath)
        # info_dict = data.setup_output_dict(request_data)
        # ...
        # return parsed_data

        """ parse_form.py hasn't been written yet. """


    def parse_pa_data(self, panel_id, panel_version):
        """ Use parse_pa.py to import and clean PanelApp data """

        data = parse_pa.Data(
            panel_id = panel_id,
            panel_version = panel_version)

        # retrieve panel data from PanelApp
        panel = data.get_panelapp_panel(panel_id, panel_version)

        # set up dict to hold relevant panel data
        info_dict = data.setup_output_dict(panel)

        # update dict with panel gene data
        info_dict = data.parse_gene_info(panel, info_dict)

        # update dict with panel region data
        parsed_data = data.parse_region_info(panel, info_dict)

        return parsed_data


    def handle(self, *args, **kwargs):
        """ Coordinates functions to import and parse data from
        specified source, then calls insert.py to insert cleaned data
        into the database. """

        # source must be specified

        if args['source']:

            source = args['source'][0]

            # import test directory data (td_source and td_current required)

            if (source == 'd') and \
                (kwargs['--td_source']) and \
                (kwargs['--td_current']):

                td_source = kwargs['--td_source'][0]
                td_current = kwargs['--td_current'][0]

                parsed_data = self.import_td_data(td_source, td_current)
                type = 'directory'


            # import and parse data from a request form (filepath required)

            if (source == 'f') and \
                (kwargs['--filepath']):

                # filepath = kwargs['--filepath'][0]

                # parsed_data = self.parse_form_data(filepath)
                # type = 'panel'

                print("The app can't deal with request forms yet.")


            # import and parse an unmodified PanelApp panel (panel id required)

            elif (source == 'p') and \
                (kwargs['--panel_id']):

                panel_id = kwargs['--panel_id'][0]

                if kwargs['--panel_version']:
                    panel_version = kwargs['--panel_version'][0]

                else:
                    panel_version = None  # gets current panel version

                parsed_data = self.parse_pa_data(panel_id, panel_version)
                type = 'panel'


            # a valid combination of arguments is required

            else:
                print('Error reading in arguments. \
                    \nSpecified source: {} \
                    \nSupplied args: {} \
                    \nSupplied kwargs: {}'.format(source, args, kwargs))


            # insert the parsed data into the db

            inserter.insert_data(parsed_data, type)


        else:
            print("Data source must be specified. Options are d for test \
                directory, f for request form, or p for PanelApp.")
