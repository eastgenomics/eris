"""

Coordinates the functions to:

    1. Pull in and parse data from...
        a. an unmodified PanelApp panel (via parse_pa.py)
        b. a request form (via parse_form.py)

    2. Insert the parsed data into the database (via insert.py)


Usage:
python manage.py seed <source> <options>

Options (*not required, defaults to None):
    source: f (request form) or p (PanelApp) to specify source of panel
    *infile [str]: Path to request form file (if source=f)
    *panel_id [str]: PanelApp panel id (if source=p)
    *panel_version [str]: Optional PanelApp panel version (if source=p)

Example: Import a panel from a request form
python manage.py seed f --infile '<path to form>'

Example: Import current version of an unmodified PanelApp panel
python manage.py seed p --panel_id '<id>'

Example: Import older version of an unmodified PanelApp panel
python manage.py seed p --panel_id '<id>' --panel_version '<version>'

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

        parser.add_argument(
            "source",
            help = "Valid options: 'f' for form or 'p' for PanelApp",
			nargs = 1,)

        parser.add_argument(
            "--infile",
            help = "Path to request form file",
			nargs = '?',)

        parser.add_argument(
            "--panel_id",
            help = "PanelApp panel id",
			nargs = '?',)

        parser.add_argument(
            "--panel_version",
            help = "PanelApp panel version (optional), defaults to None",
			nargs = '?',)


    def parse_pa_data(self, options):
        """ Use functions in parse_pa.py to import and clean PanelApp
        panel data """

        
    def parse_form_data(self, options):
        """ Use functions in parse_form.py to import and clean request
        form data """


    def handle(self, *args, **kwargs):
        """ Uses parse_data to import and clean data, then calls insert.py
        to insert cleaned data into the database. """

        # Source and options need to be specified
        if args['source']:
            source = args['source'][0]


            # Section to deal with data from a request form

            if source == 'f' and kwargs['--infile']:
                form_path = kwargs['--infile'][0]

                # call to parse_form_data
                # generate cleaned_data


            # Section to deal with data from PanelApp

            elif source == 'p' and kwargs['--panel_id']:
                panel_id = kwargs['--panel_id'][0]

                if kwargs['--panel_version']:
                    panel_version = kwargs['--panel_version'][0]

                # call to parse_pa_data
                # generate cleaned_data


            # insert the parsed data into the database
            # call insert.py on cleaned_data


        # Can't do anything if you don't know the data source
        else:
            print('Invalid options supplied, see seed.py for example usage')
