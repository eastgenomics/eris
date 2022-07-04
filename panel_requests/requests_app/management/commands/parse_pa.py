
"""
This script (called in seed.py) defines functions to retrieve a panel's
data from PanelApp, and parse it for insertion into the database.
"""


### STILL TO DO: ###

# PanelApp genes don't reliably have a specific transcript defined, this needs
# addressing in here somehow

# PanelApp regions never have associated grch37 coords, need to write something
# to liftover from the grch38 ones


from panelapp import Panelapp
from panelapp import api


class Data:

    def __init__(self, panel_id, panel_version):

        self.panel_id = panel_id
        self.panel_version = panel_version


    def get_panelapp_panel(self, panel_id, panel_version):
        """ Returns a dict representing a specific version of a PanelApp
        panel. If version is not specified, retrieves the current
        version of that panel.

        Note that 'Panelapp.Panel' doesn't work for all panel versions -
        some older versions don't contain the 'hgnc_symbol' field.

        args:
            panel_id [str]: PanelApp panel ID
            panel_version [str/None]: PanelApp panel version

        returns:
            panel: dict of PanelApp data on specified version of panel
        """

        if panel_version:
            path = ["panels", panel_id]
            param = {"version": panel_version}

            url = api.build_url(path, param)
            panel = api.get_panelapp_response(url)

        else:
            panel = Panelapp.Panel(str(panel_id)).get_data()

        return panel


    def setup_output_dict(self, panel):
        """ Initialise a dict to hold relevant panel information.

        args:
            panel [dict]: PanelApp data on one panel

        returns:
            info_dict [dict]: initial dict of core panel info
        """

        info_dict = {
            'panel_source' : 'PanelApp',
            'external_id' : panel['id'],
            'panel_version' : panel['version'],
            'genes' : [],
            'regions' : [],
            }

        return info_dict


    def parse_gene_info(self, panel, info_dict):
        """ Iterate over every gene in the panel and retrieve the data
        needed to populate panel_gene and associated models.

        args:
            panel [dict]: PanelApp data on one panel
            info_dict [dict]: holds data needed to populate db models

        returns:
            info_dict [dict]: updated with gene data
        """

        for gene in panel['genes']:

            gene_dict = {
                'transcript' : gene['transcript'],  # PA doesn't always provide
                'hgnc_id' : gene['gene_data']['hgnc_id'][6:],
                'confidence_level' : gene['confidence_level'],
                'mode_of_inheritance' : gene['mode_of_inheritance'],
                'mode_of_pathogenicity' : gene['mode_of_pathogenicity'],
                'penetrance' : gene['penetrance'],
                'gene_justification' : 'PanelApp',
                'transcript_justification' : 'PanelApp',
                }

            info_dict['genes'].append(gene_dict)

        return info_dict


    def parse_region_info(self, panel, info_dict):
        """ Iterate over every region in the panel and retrieve the data
        needed to populate panel_region and associated models.

        args:
            panel [dict]: PanelApp data on one panel
            info_dict [dict]: holds data needed to populate db models

        returns:
            info_dict [dict]: updated with region data
        """

        for region in panel['regions']:

            region_dict = {
                'confidence_level' : region['confidence_level'],
                'mode_of_inheritance' : region['mode_of_inheritance'],
                'mode_of_pathogenicity' : region['mode_of_pathogenicity'],
                'penetrance' : region['penetrance'],
                'name' : region['verbose_name'],
                'chrom' : region['chromosome'],
                'start_37' : None,  # need to liftover from grch38
                'end_37' : None,
                'start_38' : region['grch38_coordinates'][0],
                'end_38' : region['grch38_coordinates'][1],
                'type' : 'CNV',  # all PA regions are CNVs
                'variant_type' : region['variant_type'],
                'required_overlap' : region['required_overlap'],
                'haploinsufficiency' : region['haploinsufficiency_score'],
                'triplosensitivity' : region['triplosensitivity_score'],
                'justification' : 'PanelApp',
                }

            info_dict['regions'].append(region_dict)

        return info_dict
