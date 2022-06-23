
"""
This script (called in seed.py) will define functions to import panel
data from a request form and parse it for insertion into the database.
"""


### work on this is waiting until the panelapp route is working


class Data:

    def __init__(self, filepath):
        self.filepath = filepath


    def get_form_data(self, filepath):
        """ Pull in data from the request form file.

        args:
            filepath [str]: path to request form

        returns:
            request_data: form contents as some sort of data object
        """


    def setup_output_dict(self, request_data):
        """

        args:
            request_data: form contents as some sort of data object

        returns:
            info_dict [dict]: initial dict of core panel info
        """
