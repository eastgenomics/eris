
"""
This script (called in seed.py) will define functions to import panel
data from a request form and parse it for insertion into the database.
"""


import pandas as pd
from openpyxl import load_workbook


class FormParser:

    def __init__(self, filepath):
        self.filepath = filepath

    def get_form_data(self, fp):
        """ Pull in data from the request form file and parse into 4
        pandas DFs - general request info, panels info, genes, and
        regions.

        args:
            fp [str]: path to request form

        returns:
            form_contents []: entire unparsed file contents
        """

        wb = load_workbook(filename=fp)
        ws = wb.active

        # identify row boundaries of each data table
        # this assumes there is -exactly- one blank row between each table

        row_count = 1

        for row in ws.iter_rows(max_col=1, values_only=True):
            if row[0] == 'Current panels':
                p_start = row_count + 1

            elif row[0] == 'Gene symbol':
                g_start = row_count + 1
                p_end = row_count - 2

            elif row[0] == 'Region name':
                r_start = row_count + 1
                g_end = row_count - 2

            elif row[0] == 'END OF FORM':
                r_end = row_count - 5
                break

            row_count += 1

        # create dict of general request info

        general_info = {
            'Request date': ws['B1'].value,
            'Requested by': ws['B2'].value,
            'Clinical indication': ws['B3'].value,
            'Reference genome': ws['B4'].value,
            'Form generated': ws['B5'].value}

        # create df from panels info

        panel_df = pd.DataFrame({
            'Current panels':
                [cell[0].value for cell in ws[f'A{p_start}': f'A{p_end}']],
            'Panel source':
                [cell[0].value for cell in ws[f'B{p_start}': f'B{p_end}']],
            'External ID':
                [cell[0].value for cell in ws[f'C{p_start}': f'C{p_end}']],
            'External version':
                [cell[0].value for cell in ws[f'D{p_start}': f'D{p_end}']]})

        # create df from genes info

        gene_df = pd.DataFrame({
            'Gene symbol':
                [cell[0].value for cell in ws[f'A{g_start}': f'A{g_end}']],
            'HGNC ID':
                [cell[0].value for cell in ws[f'B{g_start}': f'B{g_end}']],
            'Gene justification':
                [cell[0].value for cell in ws[f'C{g_start}': f'C{g_end}']],
            'Transcript':
                [cell[0].value for cell in ws[f'D{g_start}': f'D{g_end}']],
            'Transcript justification':
                [cell[0].value for cell in ws[f'E{g_start}': f'E{g_end}']],
            'Confidence':
                [cell[0].value for cell in ws[f'F{g_start}': f'F{g_end}']],
            'Penetrance':
                [cell[0].value for cell in ws[f'G{g_start}': f'G{g_end}']],
            'MOP':
                [cell[0].value for cell in ws[f'H{g_start}': f'H{g_end}']],
            'MOI':
                [cell[0].value for cell in ws[f'I{g_start}': f'I{g_end}']]})

        # create df from regions info

        region_df = pd.DataFrame({
            'Region name':
                [cell[0].value for cell in ws[f'A{r_start}': f'A{r_end}']],
            'Chromosome':
                [cell[0].value for cell in ws[f'B{r_start}': f'B{r_end}']],
            'Start':
                [cell[0].value for cell in ws[f'C{r_start}': f'C{r_end}']],
            'End':
                [cell[0].value for cell in ws[f'D{r_start}': f'D{r_end}']],
            'Justification':
                [cell[0].value for cell in ws[f'E{r_start}': f'E{r_end}']],
            'Confidence':
                [cell[0].value for cell in ws[f'F{r_start}': f'F{r_end}']],
            'Penetrance':
                [cell[0].value for cell in ws[f'G{r_start}': f'G{r_end}']],
            'MOP':
                [cell[0].value for cell in ws[f'H{r_start}': f'H{r_end}']],
            'MOI':
                [cell[0].value for cell in ws[f'I{r_start}': f'I{r_end}']],
            'Type':
                [cell[0].value for cell in ws[f'J{r_start}': f'J{r_end}']],
            'Variant type':
                [cell[0].value for cell in ws[f'K{r_start}': f'K{r_end}']],
            'Haploinsufficiency':
                [cell[0].value for cell in ws[f'L{r_start}': f'L{r_end}']],
            'Triplosensitivity':
                [cell[0].value for cell in ws[f'M{r_start}': f'M{r_end}']],
            'Overlap':
                [cell[0].value for cell in ws[f'N{r_start}': f'N{r_end}']]})

        return general_info, panel_df, gene_df, region_df

    def setup_output_dict(self, ci, req_date, panel_df):
        """ Initialise a dict to hold relevant panel information.

        args:
            panel [dict]: PanelApp data for one panel

        returns:
            info_dict [dict]: initial dict of core panel info
        """

        # I'm assuming that we want to store the external IDs and versions of
        # the original PA panels that a custom panel is based on?

        pa_ids = [value for value in panel_df['External ID']]
        pa_versions = [value for value in panel_df['External version']]

        info_dict = {
            'ci': ci,
            'req_date': req_date,
            'panel_source': 'Request',
            'panel_name': f'{ci}_request_{req_date}',
            'external_id': pa_ids,  # will be a list...
            'panel_version': pa_versions,
            'genes': [],
            'regions': [],
            }

        return info_dict

    def parse_genes(self, info_dict, gene_df):
        """ Iterate over every gene in the panel and retrieve the data
        needed to populate panel_gene and associated models. Only use
        genes with 'confidence_level' == '3'; i.e. 'green' genes.

        args:
            panel [dict]: PanelApp data on one panel
            info_dict [dict]: holds data needed to populate db models

        returns:
            info_dict [dict]: updated with gene data
        """

        for row in gene_df.iterrows():

            gene_dict = {
                'hgnc_id': row[1]['HGNC ID'],
                'gene_justification': row[1]['Gene justification'],
                'confidence_level': row[1]['Confidence'],
                'mode_of_inheritance': row[1]['MOI'],
                'mode_of_pathogenicity': row[1]['MOP'],
                'penetrance': row[1]['Penetrance'],
                'transcript': row[1]['Transcript'],
                'transcript_justification': row[1]['Transcript justification']}

            info_dict['genes'].append(gene_dict)

        return info_dict

    def parse_regions(self, ref_genome, info_dict, region_df):
        """ Iterate over every region in the panel and retrieve the data
        needed to populate panel_region and associated models. Only use
        regions with 'confidence_level' == '3'; i.e. 'green' regions.

        args:
            panel [dict]: PanelApp data for one panel
            info_dict [dict]: holds data needed to populate db models

        returns:
            info_dict [dict]: updated with region data
        """

        for row in region_df.iterrows():

            region_dict = {
                'confidence_level': row[1]['Confidence'],
                'mode_of_inheritance': row[1]['MOI'],
                'mode_of_pathogenicity': row[1]['MOP'],
                'penetrance': row[1]['Penetrance'],
                'name': row[1]['Region name'],
                'chrom': row[1]['Chromosome'],
                'start': row[1]['Start (GRCh37)'],
                'end': row[1]['End (GRCh37)'],
                'type': row[1]['Type'],
                'variant_type': row[1]['Variant type'],
                'required_overlap': row[1]['Overlap'],
                'haploinsufficiency': row[1]['Haploinsufficiency'],
                'triplosensitivity': row[1]['Triplosensitivity'],
                'justification': row[1]['Justification']}

            info_dict['regions'].append(region_dict)

        return info_dict
