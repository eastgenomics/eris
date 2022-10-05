#!usr/bin/env python

"""
Given a clinical indication (CI) code, acquires the panel currently
associated with that CI in the database and uses it to populate an Excel
request form.

Generic and example usages can be found in the README.
"""


import pandas as pd
import xlsxwriter

from . import functions_hgnc

from copy import copy
from datetime import datetime as dt
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import NamedStyle, Font, PatternFill, Alignment

from django.core.management.base import BaseCommand

from requests_app.models import (
    Panel,
    ClinicalIndication,
    ClinicalIndicationPanel,
    Hgnc,
    Gene,
    Confidence,
    Penetrance,
    ModeOfInheritance,
    ModeOfPathogenicity,
    PanelGene,
    Transcript,
    PanelGeneTranscript,
    Haploinsufficiency,
    Triplosensitivity,
    RequiredOverlap,
    VariantType,
    Region,
    PanelRegion)


class Command(BaseCommand):
    help = "Given a clinical indication (CI) code, acquires the panel " \
        "currently associated with that CI in the database and uses it " \
        "to populate an Excel request form."

    def add_arguments(self, parser):
        """ Define the CI to generate a request form for """

        parser.add_argument(
            "req_date",
            nargs=1,
            help="Date the request was submitted",)

        parser.add_argument(
            "requester",
            nargs=1,
            help="Person who submitted the request",)

        parser.add_argument(
            "ci_code",
            nargs=1,
            help="The CI code to create request form for (e.g. R149.1)",)

        parser.add_argument(
            "ref_genome",
            nargs=1,
            choices=['GRCh37', 'GRCh38'],
            help="The reference genome build to use",)

        parser.add_argument(
            "hgnc_dump",
            nargs=1,
            help="Name of HGNC dump text file")

    def get_panel_records(self, ci_code, ref_genome):
        """ Retrieve Panel records from the database where the panel is
        associated with the specified CI code and reference genome
        version, and where that panel is currently in use for the
        specified clinical indication.

        args:
            ci_code [str]: supplied at command line
            ref_genome [str]: supplied at command line

        returns:
            panel_records [list of dicts]: each dict is one panel record
        """

        panel_records = Panel.objects.filter(
            clinicalindicationpanel__clinical_indication_id__code=ci_code,
            reference_genome__reference_build=ref_genome,
            clinicalindicationpanel__current=True).values()

        return panel_records

    def retrieve_panel_entities(self, ref_genome, panel_records):
        """ For each retrieved panel record, retrieve all associated
        gene and region records and combine in a dict. Return a list of
        these dicts.

        args:
            ref_genome [str]: supplied at command line
            panel_records [list of dicts]: list of Panel records

        returns:
            panel_dicts [list of dicts]: formatted data for each panel
        """

        panel_dicts = []

        for panel_dict in panel_records:

            panel_genome = ref_genome

            panel_genes = self.get_gene_records(panel_dict)
            panel_regions = self.get_region_records(panel_dict)

            panel_data = {
                'name': panel_dict['panel_name'],
                'int_id': panel_dict['id'],
                'source': panel_dict['panel_source'],
                'ext_id': panel_dict['external_id'],
                'ext_version': panel_dict['panel_version'],
                'ref_genome': panel_genome,
                'genes': panel_genes,
                'regions': panel_regions}

            panel_dicts.append(panel_data)

        return panel_dicts

    def get_gene_records(self, panel_dict):
        """ Retrieve all gene records associated with a panel record.

        args:
            panel_dict [dict]: information about a single panel record

        returns:
            gene_data [list of dicts]: each element is info on one gene
        """

        gene_data = []

        panel_genes = PanelGene.objects.filter(
            panel_id=panel_dict['id']).values()

        if len(panel_genes) > 0:

            for gene in panel_genes:

                transcript = Transcript.objects.filter(
                    panelgenetranscript__panel_gene_id=gene['id']
                    ).values()[0]['refseq_id']

                transcript_reason = PanelGeneTranscript.objects.filter(
                    panel_gene_id=gene['id']
                    ).values()[0]['justification']

                hgnc = Hgnc.objects.filter(
                    gene__panelgene__id=gene['id']
                    ).values()[0]['id']

                confidence = Confidence.objects.filter(
                    panelgene__id=gene['id']
                    ).values()[0]['confidence_level']

                moi = ModeOfInheritance.objects.filter(
                    panelgene__id=gene['id']
                    ).values()[0]['mode_of_inheritance']

                mop = ModeOfPathogenicity.objects.filter(
                    panelgene__id=gene['id']
                    ).values()[0]['mode_of_pathogenicity']

                penetrance = Penetrance.objects.filter(
                    panelgene__id=gene['id']
                    ).values()[0]['penetrance']

                gene_dict = {
                    'transcript': transcript,
                    'hgnc': hgnc,
                    'conf': confidence,
                    'moi': moi,
                    'mop': mop,
                    'pen': penetrance,
                    'gene_reason': gene['justification'],
                    'trans_reason': transcript_reason}

                gene_data.append(gene_dict)

        return gene_data

    def get_region_records(self, panel_dict):
        """ Retrieve all region records associated with a panel record.

        args:
            panel_dict [dict]: information about a single panel record

        returns:
            region_data [list of dicts]: each element is info on one region
        """

        region_data = []

        panel_regions = PanelRegion.objects.filter(
            panel_id=panel_dict['id']).values()

        if len(panel_regions) > 0:

            for region in panel_regions:

                confidence = Confidence.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['confidence_level']

                moi = ModeOfInheritance.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['mode_of_inheritance']

                mop = ModeOfPathogenicity.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['mode_of_pathogenicity']

                penetrance = Penetrance.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['penetrance']

                name = Region.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['name']

                chromosome = Region.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['chrom']

                start = Region.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['start']

                end = Region.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['end']

                region_type = Region.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['type']

                variant_type = VariantType.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['variant_type']

                haplo = Haploinsufficiency.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['haploinsufficiency']

                triplo = Triplosensitivity.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['triplosensitivity']

                overlap = RequiredOverlap.objects.filter(
                    panelregion__id=region['id']
                    ).values()[0]['required_overlap']

                region_dict = {
                    'conf': confidence,
                    'moi': moi,
                    'mop': mop,
                    'pen': penetrance,
                    'name': name,
                    'chrom': chromosome,
                    'start': start,
                    'end': end,
                    'type': region_type,
                    'var_type': variant_type,
                    'haplo': haplo,
                    'triplo': triplo,
                    'overlap': overlap,
                    'reason': region['justification']}

                region_data.append(region_dict)

        return region_data

    def create_generic_df(self, req_date, requester, ci_code, ref_genome):
        """ Create a header dataframe of general request information.

        args:
            req_date [str]: supplied at command line
            requester [str]: supplied at command line
            ci_code [str]: supplied at command line
            ref_genome [str]: supplied at command line

        returns:
            generic_df [pandas dataframe]
        """

        base_df = pd.DataFrame({
            'fields': [
                'Request date',
                'Requested by',
                'Clinical indication',
                'Reference genome',
                'Form generated'],
            'data': [
                req_date,
                requester,
                ci_code,
                ref_genome,
                str(dt.today())]})

        generic_df = base_df.set_index('fields')

        return generic_df

    def create_panel_df(self, panel_dicts):
        """ Create a dataframe of information about panels currently
        associated with the specified clinical indication.

        args:
            panel_dicts [list of dicts]: each dict is one panel

        returns:
            panel_df [pandas dataframe]
        """

        # dataframe columns are lists of data elements

        sources = [panel['source'] for panel in panel_dicts]
        names = [panel['name'] for panel in panel_dicts]
        ids = [panel['ext_id'] for panel in panel_dicts]
        versions = [panel['ext_version'] for panel in panel_dicts]

        # create the df

        panel_df = pd.DataFrame({
            'Current panels': names,
            'Panel source': sources,
            'External ID': ids,
            'External version': versions})

        return panel_df

    def create_gene_df(self, hgnc_df, panel_dicts):
        """ Create a dataframe listing all genes currently covered by
        the specified CI's panels.

        args:
            panel_dicts [list of dicts]: each dict is one panel

        returns:
            gene_df [pandas dataframe]
        """

        # initialise df columns

        gene_symbols = []
        hgncs = []
        gene_reasons = []
        transcripts = []
        trans_reasons = []
        confs = []
        pens = []
        mops = []
        mois = []

        # populate columns

        for panel in panel_dicts:
            for gene in panel['genes']:

                hgncs.append(gene['hgnc'])
                gene_reasons.append(gene['gene_reason'])
                transcripts.append(gene['transcript'])
                trans_reasons.append(gene['trans_reason'])
                confs.append(gene['conf'])
                pens.append(gene['pen'])
                mops.append(gene['mop'])
                mois.append(gene['moi'])

        # get current gene symbols for HGNC ids

        for hgnc_id in hgncs:

            symbol = functions_hgnc.get_symbol_from_hgnc(hgnc_df, hgnc_id)

            if symbol:

                gene_symbols.append(symbol)

            else:

                gene_symbols.append('')  # else list is the wrong length
                print(f'Problem with HGNC number: {hgnc_id}')

        # create df

        gene_df = pd.DataFrame({
            'Gene symbol': gene_symbols,
            'HGNC ID': hgncs,
            'Gene justification': gene_reasons,
            'Transcript': transcripts,
            'Transcript justification': trans_reasons,
            'Confidence': confs,
            'Penetrance': pens,
            'MOP': mops,
            'MOI': mois})

        return gene_df

    def create_region_df(self, panel_dicts):
        """ Create a dataframe listing all regions currently covered by
        the specified CI's panels.

        args:
            panel_dicts [list of dicts]: each dict is one panel

        returns:
            region_df [pandas dataframe]
        """

        # initialise df columns

        names = []
        chroms = []
        starts = []
        ends = []
        reasons = []
        confs = []
        pens = []
        mops = []
        mois = []
        haplos = []
        triplos = []
        types = []
        var_types = []
        overlaps = []

        # populate columns

        for panel in panel_dicts:
            for region in panel['regions']:

                names.append(region['name'])
                chroms.append(region['chrom'])
                starts.append(region['start'])
                ends.append(region['end'])
                reasons.append(region['reason'])
                confs.append(region['conf'])
                pens.append(region['pen'])
                mops.append(region['mop'])
                mois.append(region['moi'])
                types.append(region['type'])
                var_types.append(region['var_type'])
                haplos.append(region['haplo'])
                triplos.append(region['triplo'])
                overlaps.append(region['overlap'])

        # create df

        region_df = pd.DataFrame({
            'Region name': names,
            'Chromosome': chroms,
            'Start': starts,
            'End': ends,
            'Justification': reasons,
            'Confidence': confs,
            'Penetrance': pens,
            'MOP': mops,
            'MOI': mois,
            'Type': types,
            'Variant type': var_types,
            'Haploinsufficiency': haplos,
            'Triplosensitivity': triplos,
            'Overlap': overlaps})

        return region_df

    def create_blank_dfs(self):
        """ For cases where a clinical indication has no associated
        current panels, create blank dfs for genes and regions to be
        added to.

        returns:
            gene_df [pandas dataframe]
            region_df [pandas dataframe]
        """

        gene_df = pd.DataFrame({
            'Gene symbol': ['e.g. ADCY5', '',
                'Insert data for 1 gene/row - add rows as required'],
                'HGNC ID': ['e.g. 236', '', ''],
                'Gene justification': ['e.g. PanelApp', '', ''],
                'Transcript': ['e.g. NM_183357.3', '', ''],
                'Transcript justification': ['e.g. MANE', '', ''],
                'Confidence': ['e.g. 3', '', ''],
                'Penetrance': ['e.g. Complete', '', ''],
                'MOP': ['e.g. gain-of-function', '', ''],
                'MOI': ['e.g. MITOCHONDRIAL', '', '']})

        region_df = pd.DataFrame({
            'Region name': [
                'e.g. Xp11.23 region (includes MAOA and MAOB) Loss', '',
                'Insert data for 1 region/row - add rows as required'],
                'Chromosome': ['e.g. X', '', ''],
                'Start': ['e.g. 43654906', '', ''],
                'End': ['e.g. 43882474', '', ''],
                'Justification': ['e.g. PanelApp', '', ''],
                'Confidence': ['e.g. 3', '', ''],
                'Penetrance': ['e.g. Incomplete', '', ''],
                'MOP': ['e.g. gain-of-function', '', ''],
                'MOI': ['e.g. MITOCHONDRIAL', '', ''],
                'Type': ['e.g. cnv', '', ''],
                'Variant type': ['e.g. cnv_loss', '', ''],
                'Haploinsufficiency': ['e.g. 3', '', ''],
                'Triplosensitivity': ['e.g. 2', '', ''],
                'Overlap': ['N/A', '', '']})

        return gene_df, region_df

    def write_blank_form(self, filename, generic_df, gene_df, region_df):
        """ Construct a blank request form as an Excel file. This will
        be executed if there are no panels in the database currently
        associated with the specified clinical indication.

        args:
            filename [str]: name of output request form
            generic_df [pandas dataframe]: general info about request
            gene_df [pandas dataframe]: all genes covered by these panels
            region_df [pandas dataframe]: all regions covered by these panels

        returns:
            cell_ranges [list]: strs of cell ranges (e.g. 'A1:A7')
        """

        writer = pd.ExcelWriter(filename, engine='xlsxwriter')

        row = 0
        col = 0
        header_rows = []

        # write generic df in cell A1, increment row by df length

        generic_df.to_excel(
            writer,
            sheet_name='Sheet1',
            startrow=row,
            startcol=col,
            header=False)

        for df_row in generic_df.iterrows():
            row += 1

        row += 1

        # write gene df, get range of header

        gene_df.to_excel(
            writer,
            sheet_name='Sheet1',
            startrow=row,
            startcol=col,
            index=False)

        header_rows.append(('gene', row + 1))

        # increment row by df length

        for df_row in gene_df.iterrows():
            row += 1

        row += 2

        # write region df, get range of header

        region_df.to_excel(
            writer,
            sheet_name='Sheet1',
            startrow=row,
            startcol=col,
            index=False)

        header_rows.append(('region', row + 1))

        # identify the last populated row

        for df_row in region_df.iterrows():
            row += 1

        final_row = row + 6

        writer.save()

        return header_rows, final_row

    def write_data(self, filename, generic_df, panel_df, gene_df, region_df):
        """ Construct the request form as an excel file.

        args:
            filename [str]: for output request form
            generic_df [pandas dataframe]: general info about request
            panel_df [pandas dataframe]: list of current panels for this CI
            gene_df [pandas dataframe]: all genes covered by these panels
            region_df [pandas dataframe]: all regions covered by these panels

        returns:
            cell_ranges [list]: strs of cell ranges (e.g. 'A1:A7')
        """

        writer = pd.ExcelWriter(filename, engine='xlsxwriter')

        row = 0
        col = 0
        header_rows = []

        # write generic df in cell A1, increment row by df length

        generic_df.to_excel(
            writer,
            sheet_name='Sheet1',
            startrow=row,
            startcol=col,
            header=False)

        for df_row in generic_df.iterrows():
            row += 1

        row += 1  # spacer between dataframes

        # write panel df, get row of header, increment row by df length

        panel_df.to_excel(
            writer,
            sheet_name='Sheet1',
            startrow=row,
            startcol=col,
            index=False)

        header_rows.append(('panel', row + 1))

        for df_row in panel_df.iterrows():
            row += 1

        row += 2

        # write gene df, get row of header, increment row by df length

        gene_df.to_excel(
            writer,
            sheet_name='Sheet1',
            startrow=row,
            startcol=col,
            index=False)

        header_rows.append(('gene', row + 1))

        for df_row in gene_df.iterrows():
            row += 1

        row += 2

        # write region df, get row of header

        region_df.to_excel(
            writer,
            sheet_name='Sheet1',
            startrow=row,
            startcol=col,
            index=False)

        header_rows.append(('region', row + 1))

        # identify the last populated row

        for df_row in region_df.iterrows():
            row += 1

        final_row = row + 6

        writer.save()

        return header_rows, final_row

    def format_excel(self, excel_file, cell_ranges, final_row):
        """ Visually format an existing excel file. Apply a style to
        dataframe header cells, and set column widths to autofit data.

        args:
            excel_file [str]: path to file
            cell_ranges [list]: strs (e.g. 'A1:A7') of cell ranges for styling
        """

        # load in the excel file

        wb = load_workbook(filename=excel_file)
        ws = wb['Sheet1']

        # define a style for a default font type and size

        normal_font = NamedStyle(name="normal_font")

        normal_font.font = Font(name='Arial', size=10)

        normal_font.alignment = Alignment(
            horizontal='left', vertical='center')

        wb.add_named_style(normal_font)

        # define a style to highlight column headings

        col_headings = NamedStyle(name="col_headings")

        col_headings.font = Font(name='Arial', size=10, bold=True)

        col_headings.alignment = Alignment(
            horizontal='left', vertical='center')

        col_headings.fill = PatternFill(
            fill_type='solid',
            start_color='00C0C0C0',  # light grey
            end_color='00C0C0C0')

        wb.add_named_style(col_headings)

        # define a style to highlight the end of the form

        highlight = NamedStyle(name="highlight")

        highlight.font = Font(name='Arial', size=10, bold=True)

        highlight.alignment = Alignment(
            horizontal='left', vertical='center')

        highlight.fill = PatternFill(
            fill_type='solid',
            start_color='00FFCC00',  # yellow
            end_color='00FFCC00')

        wb.add_named_style(highlight)

        # apply the default font to all populated cells

        for col in 'ABCDEFGHIJKLMN':
            for row in range(1, final_row + 1):

                ws[f'{col}{row}'].style = 'normal_font'

        # apply the heading style to the index of the generic df

        for row in range(1, 6):

            ws[f'A{row}'].style = 'col_headings'

        # apply the heading style to the headers of the other dfs

        for cell_range in cell_ranges:

            row = cell_range[1]

            if cell_range[0] == 'panel':

                cols = 'ABCD'

            elif cell_range[0] == 'gene':

                cols = 'ABCDEFGHI'

            elif cell_range[0] == 'region':

                cols = 'ABCDEFGHIJKLMN'

            for col in cols:

                ws[f'{col}{row}'].style = 'col_headings'

        # mark the final rows

        ws[f'A{final_row - 2}'] = 'Please do not change any headings, ' \
            'or the order of the columns.'

        ws[f'A{final_row}'] = 'END OF FORM'
        ws[f'B{final_row}'] = 'Please do not enter anything below this row.'

        for row in [final_row - 2, final_row]:
            for col in ['A', 'B', 'C']:

                ws[f'{col}{row}'].style = 'highlight'

        # set all columns to be 5cm wide

        for col in 'ABCDEFGHIJKLMN':

            ws.column_dimensions[col].width = 25.5

        wb.save(filename=excel_file)

    def handle(self, *args, **kwargs):
        """ Execute the functions to create a request form """

        # read in arguments (all are required)

        if kwargs['req_date'] and \
            kwargs['requester'] and \
            kwargs['ci_code'] and \
            kwargs['ref_genome'] and \
            kwargs['hgnc_dump']:

            req_date = kwargs['req_date'][0]
            requester = kwargs['requester'][0]
            ci_code = kwargs['ci_code'][0]
            ref_genome = kwargs['ref_genome'][0]
            hgnc_dump = kwargs['hgnc_dump'][0]

            # retrieve records of panels currently linked to that CI code

            panel_records = self.get_panel_records(ci_code, ref_genome)

            # construct header df of general info about the request

            generic_df = self.create_generic_df(
                req_date,
                requester,
                ci_code,
                ref_genome)

            # if that CI currently has no panels, create a blank form

            if len(panel_records) == 0:

                print('No panels are currently associated with this '
                    'clinical indication.')

                # create blank gene/region dfs

                gene_df, region_df = self.create_blank_dfs()

                # write a blank form

                filename = 'request_form_' \
                    f'{req_date}_{ci_code}_{ref_genome}_{requester}_BLANK.xlsx'

                header_ranges, final_row = self.write_blank_form(
                    filename,
                    generic_df,
                    gene_df,
                    region_df)

            # if the CI has 1+ current panel, create a populated form

            else:
                # get genes and regions for each panel

                panel_dicts = self.retrieve_panel_entities(
                    ref_genome,
                    panel_records)

                # create panel, gene and region dataframes

                panel_df = self.create_panel_df(panel_dicts)
                region_df = self.create_region_df(panel_dicts)

                hgnc_df = functions_hgnc.import_hgnc_dump(hgnc_dump)
                hgnc_df = functions_hgnc.set_column_names(hgnc_df)

                gene_df = self.create_gene_df(hgnc_df, panel_dicts)

                # construct the request form and print the filename

                filename = 'request_form_' \
                    f'{req_date}_{ci_code}_{ref_genome}_{requester}.xlsx'

                header_ranges, final_row = self.write_data(
                    filename,
                    generic_df,
                    panel_df,
                    gene_df,
                    region_df)

            # apply formatting to the created file

            self.format_excel(filename, header_ranges, final_row)

            print(f'Request form created: {filename}')

        else:
            print("The following arguments are required, and must be "
                "specified in this order: request_date, requester, ci_code, "
                "ref_genome, hgnc_dump.\nValid values for ref_genome are "
                "GRCh37 and GRCh38.")
