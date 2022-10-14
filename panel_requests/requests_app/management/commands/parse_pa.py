#!usr/bin/env python

"""
This script (called within seed.py) defines functions to retrieve a
panel's data from PanelApp, and parse it for insertion into the
database.
"""

# STILL TO DO:

# PanelApp genes don't reliably have a specific transcript defined, this needs
# addressing in here somehow

# PanelApp regions never have associated grch37 coords, need to write something
# to liftover from the grch38 ones


from panelapp import Panelapp
from panelapp import api


class PanelParser:

    def __init__(self, panel_id, panel_version=None):

        self.panel_id = str(panel_id)

        if panel_version:
            self.panel_version = str(panel_version)

        else:
            self.panel_version = None

    def get_panelapp_panel(self, id, version=None):
        """ Retrieve PanelApp panel object for specified panel ID and version.

        args:
            id [str]: id of panelapp panel
            version [str/None]: gets current panel version if not specified

        returns:
            result [dict]: data for specified version of specified panel
        """

        panel_id = str(id)

        if version:
            panel_version = str(version)

        else:
            panel_version = None

        try:
            result = Panelapp.Panel(panel_id, panel_version).get_data()

        # some older panel versions are awkward for variable reasons
        except Exception as error:

            print(f'Error with 1st panel retrieval attempt: {error}')

            path = ["panels", panel_id]
            param = {"version": panel_version}

            url = api.build_url(path, param)
            result = api.get_panelapp_response(url)

        return result

    def setup_output_dict(self, panel):
        """ Initialise a dict to hold relevant panel information.

        args:
            panel [dict]: PanelApp data for one panel

        returns:
            info_dict [dict]: initial dict of core panel info
        """

        info_dict = {
            'panel_source': 'PanelApp',
            'panel_name': panel['name'],
            'external_id': panel['id'],
            'panel_version': panel['version'],
            'genes': [],
            'regions': [],
            }

        return info_dict

    def parse_gene_info(self, panel, info_dict):
        """ Iterate over every gene in the panel and retrieve the data
        needed to populate panel_gene and associated models. Only use
        genes with 'confidence_level' == '3'; i.e. 'green' genes.

        args:
            panel [dict]: PanelApp data on one panel
            info_dict [dict]: holds data needed to populate db models

        returns:
            info_dict [dict]: updated with gene data
        """

        for gene in panel['genes']:

            if gene['confidence_level'] == '3':

                gene_dict = {
                    'transcript': gene['transcript'],
                    'hgnc_id': gene['gene_data']['hgnc_id'],
                    'confidence_level': gene['confidence_level'],
                    'mode_of_inheritance': gene['mode_of_inheritance'],
                    'mode_of_pathogenicity': gene['mode_of_pathogenicity'],
                    'penetrance': gene['penetrance'],
                    'gene_justification': 'PanelApp',
                    'transcript_justification': 'PanelApp',
                    }

                info_dict['genes'].append(gene_dict)

        return info_dict

    def parse_region_info(self, panel, info_dict):
        """ Iterate over every region in the panel and retrieve the data
        needed to populate panel_region and associated models. Only use
        regions with 'confidence_level' == '3'; i.e. 'green' regions.

        args:
            panel [dict]: PanelApp data for one panel
            info_dict [dict]: holds data needed to populate db models

        returns:
            info_dict [dict]: updated with region data
        """

        for region in panel['regions']:

            if region['confidence_level'] == '3':

                region_dict = {
                    'confidence_level': region['confidence_level'],
                    'mode_of_inheritance': region['mode_of_inheritance'],
                    'mode_of_pathogenicity': region['mode_of_pathogenicity'],
                    'penetrance': region['penetrance'],
                    'name': region['verbose_name'],
                    'chrom': region['chromosome'],
                    'start_37': 'None',  # need to liftover from grch38
                    'end_37': 'None',
                    'start_38': region['grch38_coordinates'][0],
                    'end_38': region['grch38_coordinates'][1],
                    'type': 'CNV',  # all PA regions are CNVs
                    'variant_type': region['type_of_variants'],
                    'required_overlap': region['required_overlap_percentage'],
                    'haploinsufficiency': region['haploinsufficiency_score'],
                    'triplosensitivity': region['triplosensitivity_score'],
                    'justification': 'PanelApp',
                    }

                info_dict['regions'].append(region_dict)

        return info_dict
