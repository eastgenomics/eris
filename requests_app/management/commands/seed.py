"""
Coordinates functions to:

    1. Pull in and parse data from...
        a. an unmodified PanelApp panel (via parse_pa.py)
        b. a request form (via parse_form.py)

    2. Insert the parsed data into the database (via insert.py)

Usage:

    python manage.py seed <source> <options>

Options (*not always required, defaults to None):

    source: source of panel, can be 'f' (request form) or 'p' (PanelApp)
    *--infile [str]: Path to request form (required if source = 'f')
    *--panel_id [str]: PanelApp panel id (required if source = 'p')
    *--panel_version [str]: PanelApp panel version (optional if source = 'p')

Example: Import a panel from a request form

    python manage.py seed f --infile <path to form>

Example: Import current version of an unmodified PanelApp panel

    python manage.py seed p --panel_id <id>

Example: Import older version of an unmodified PanelApp panel

    python manage.py seed p --panel_id <id> --panel_version <version>

"""


from django.core.management.base import BaseCommand
import requests_app.management.commands.parse_pa as parse_pa
import requests_app.management.commands.parse_form as parse_form
import requests_app.management.commands.insert as inserter


class Command(BaseCommand):
    help = "Coordinate the functions in parse_pa_data/parse_form_data to \
        import and clean panel data, then use insert.py to insert the \
        cleaned data into the database."
    
    def add_arguments(self, parser):
        """ Define the source of the panel data to import. """

        # 'source' arg is required
        parser.add_argument(
            "source",
            help = "Options: 'f' for request form or 'p' for PanelApp",
			nargs = 1,)

        # 'filepath' kwarg is required if source = f
        parser.add_argument(
            "--filepath",
            help = "Path to request form file",
			nargs = '?',)

        # 'panel_id' kwarg is required if source = p
        parser.add_argument(
            "--panel_id",
            help = "PanelApp panel id",
			nargs = '?',)

        # 'panel_version' kwarg is optional if source = p
        parser.add_argument(
            "--panel_version",
            help = "PanelApp panel version (optional)",
			nargs = '?',)


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
        info_dict = data.parse_region_info(panel, info_dict)

        return info_dict

        
    def parse_form_data(self, filepath):
        """ Use parse_form.py to import and clean request form data """

        # parse_form.py hasn't been written yet.

        # data = parse_form.Data(filepath)
        # request_data = data.get_form_data(filepath)
        # info_dict = data.setup_output_dict(request_data)
        # ...


    def handle(self, *args, **kwargs):
        """ Coordinates functions to import and parse data from
        specified source, then calls insert.py to insert cleaned data
        into the database. """

        # Source must be specified

        if args['source']:

            source = str(args['source'][0])


            # Import and parse data from a request form (filepath required)

            if source == 'f' and kwargs['--filepath']:

                # filepath = str(kwargs['--filepath'][0])

                # parsed_data = self.parse_form_data(filepath)

                print("Sorry, the app can't deal with request forms yet.")


            # Import and parse an unmodified PanelApp panel (panel id required)

            elif source == 'p' and kwargs['--panel_id']:

                panel_id = str(kwargs['--panel_id'][0])

                if kwargs['--panel_version']:
                    panel_version = str(kwargs['--panel_version'][0])

                else:
                    panel_version = None

                parsed_data = self.parse_pa_data(panel_id, panel_version)


            else:
                print('Error reading in arguments. \
                    \nSupplied args: {} \
                    \nSupplied kwargs: {}'.format(args, kwargs))


            # call insert.py on the parsed data to insert it into the db

            inserter.insert_data(parsed_data)


        else:
            print("Data source must be specified.\n \
                Options are p for PanelApp or f for request form.")
