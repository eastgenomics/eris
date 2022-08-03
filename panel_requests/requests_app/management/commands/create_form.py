#!usr/bin/env python

"""
Given a clinical indication (CI) code, acquires the panel currently
associated with that CI in the database and uses it to populate an Excel
request form.

Usage:

    python manage.py create_form <req_date> <requester> <ci_code> <ref_genome>

Example usage (using a CI code where panel has both regions and genes):

    python manage.py create_form 20220722 JJM R149.1 GRCh37

"""


import pandas as pd
import xlsxwriter

from datetime import datetime as dt

from django.core.management.base import BaseCommand

from . import parse_pa as parse_pa
from . import parse_form as parse_form
from . import insert_panel as insert_panel
from . import insert_ci as insert_ci

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
            nargs = 1,
            help = "Date request was submitted",)

        parser.add_argument(
            "requester",
            nargs = 1,
            help = "Person who submitted the request",)

        parser.add_argument(
            "ci_code",
            nargs = 1,
            help = "CI code to create request form for",)

        parser.add_argument(
            "ref_genome",
            nargs = 1,
            choices = ['GRCh37', 'GRCh38'],
            help = "Reference genome build to use",)


    def get_panel_records(self, ci_code, ref_genome):
        """ Given a clinical indication code, retrieve Panel records of
        any panel(s) currently associated with that clinical indication.

        args:
            ci_code [str]: supplied at command line
            ref_genome [str]: supplied at command line

        returns:
            panel_records [list of dicts]: each dict is one panel record
        """

        panel_records = Panel.objects.filter(
            clinicalindicationpanel__clinical_indication_id__code = ci_code,
            reference_genome__reference_build = ref_genome,
            clinicalindicationpanel__current = True).values()

        return panel_records


    def retrieve_panel_entities(self, ref_genome, panel_records):
        """ For each panel record, retrieve all associated gene and
        region records.

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
                'int_id' : panel_dict['id'],
                'source' : panel_dict['panel_source'],
                'ext_id' : panel_dict['external_id'],
                'ext_version' : panel_dict['panel_version'],
                'ref_genome' : panel_genome,
                'genes' : panel_genes,
                'regions' : panel_regions}

            panel_dicts.append(panel_data)

        return panel_dicts


    def get_gene_records(self, panel_dict):
        """ Retrieve gene data for a single panel.

        args:
            panel_dict [dict]

        returns:
            gene_data [list of dicts]
        """

        gene_data = []

        panel_genes = PanelGene.objects.filter(
            panel_id = panel_dict['id']).values()

        if len(panel_genes) > 0:

            for gene in panel_genes:

                transcript = Transcript.objects.filter(
                    panelgenetranscript__panel_gene_id = gene['id']
                    ).values()[0]['refseq_id']

                transcript_reason = PanelGeneTranscript.objects.filter(
                    panel_gene_id = gene['id']
                    ).values()[0]['justification']

                hgnc = Hgnc.objects.filter(
                    gene__panelgene__id = gene['id']
                    ).values()[0]['id']

                confidence = Confidence.objects.filter(
                    panelgene__id = gene['id']
                    ).values()[0]['confidence_level']

                moi = ModeOfInheritance.objects.filter(
                    panelgene__id = gene['id']
                    ).values()[0]['mode_of_inheritance']

                mop = ModeOfPathogenicity.objects.filter(
                    panelgene__id = gene['id']
                    ).values()[0]['mode_of_pathogenicity']

                penetrance = Penetrance.objects.filter(
                    panelgene__id = gene['id']
                    ).values()[0]['penetrance']

                gene_dict = {
                    'transcript' : transcript,
                    'hgnc' : hgnc,
                    'conf' : confidence,
                    'moi' : moi,
                    'mop' : mop,
                    'pen' : penetrance,
                    'gene_reason' : gene['justification'],
                    'trans_reason' : transcript_reason,}

                gene_data.append(gene_dict)

        return gene_data


    def get_region_records(self, panel_dict):
        """ Retrieve region data for a single panel.

        args:
            panel_dict [dict]:

        returns:
            region_data [list of dicts]
        """

        region_data = []

        panel_regions = PanelRegion.objects.filter(
            panel_id = panel_dict['id']).values()

        if len(panel_regions) > 0:

            for region in panel_regions:

                confidence = Confidence.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['confidence_level']

                moi = ModeOfInheritance.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['mode_of_inheritance']

                mop = ModeOfPathogenicity.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['mode_of_pathogenicity']

                penetrance = Penetrance.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['penetrance']

                name = Region.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['name']

                chromosome = Region.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['chrom']

                start = Region.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['start']

                end = Region.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['end']

                region_type = Region.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['type']

                variant_type = VariantType.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['variant_type']

                haplo = Haploinsufficiency.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['haploinsufficiency']

                triplo = Triplosensitivity.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['triplosensitivity']

                overlap = RequiredOverlap.objects.filter(
                    panelregion__id = region['id']
                    ).values()[0]['required_overlap']

                region_dict = {
                    'conf' : confidence,
                    'moi' : moi,
                    'mop' : mop,
                    'pen' : penetrance,
                    'name' : name,
                    'chrom' : chromosome,
                    'start' : start,
                    'end' : end,
                    'type' : region_type,
                    'var_type' : variant_type,
                    'haplo' : haplo,
                    'triplo' : triplo,
                    'overlap' : overlap,
                    'reason' : region['justification']}

                region_data.append(region_dict)

        return region_data


    def create_head_df(self, req_date, requester, ci_code, ref_genome):
        """ Create a dataframe of general request information.

        args:
            req_date [str]: supplied at command line
            requester [str]: supplied at command line
            ci_code [str]: supplied at command line
            ref_genome [str]: supplied at command line

        returns:
            head_df [pandas dataframe]
        """

        base_df = pd.DataFrame({
            'fields' : [
                'Request date',
                'Requested by',
                'Clinical indication',
                'Reference genome',
                'Form generated'],
            'data' : [
                req_date,
                requester,
                ci_code,
                ref_genome,
                dt.today()]})

        head_df = base_df.set_index('fields')

        return head_df


    def create_panel_df(self, panel_dicts):
        """ Create a dataframe of information about panels currently
        associated with the relevant clinical indication.

        args:
            panel_dicts [list of dicts]

        returns:
            panel_df [pandas dataframe]
        """

        # create lists to populate columns

        sources = [panel['source'] for panel in panel_dicts]
        ids = [panel['ext_id'] for panel in panel_dicts]
        versions = [panel['ext_version'] for panel in panel_dicts]

        # check lists are all the same length

        if (len(sources) == len(ids)) and \
            (len(sources) == len(versions)):

            # if they are, make the df

            panel_df = pd.DataFrame({
                'Current panels' : [''] * len(sources),
                'Panel source': sources,
                'External ID': ids,
                'External version' : versions})

        else:

            print('Columns of panel_df are different lengths.\n' \
                'sources: {}\n' \
                'ids: {}\n' \
                'versions: {}'.format(sources, ids, versions))

            panel_df = 'problem with panel df'

        return panel_df


    def create_gene_df(self, panel_dicts):
        """ Create a dataframe of genes covered by the clinical
        indication's current panels.

        args:
            panel_dicts [list of dicts]

        returns:
            gene_df [pandas dataframe]
        """

        # initialise df columns

        hgncs = []
        transcripts = []
        confs = []
        mois = []
        mops = []
        pens = []
        gene_reasons = []
        trans_reasons = []

        # populate columns

        for panel in panel_dicts:
            for gene in panel['genes']:

                hgncs.append(gene['hgnc'])
                transcripts.append(gene['transcript'])
                confs.append(gene['conf'])
                mois.append(gene['moi'])
                mops.append(gene['mop'])
                pens.append(gene['pen'])
                gene_reasons.append(gene['gene_reason'])
                trans_reasons.append(gene['trans_reason'])

        # create df

        gene_df = pd.DataFrame({
            'HGNC ID': hgncs,
            'Transcript': transcripts,
            'Confidence': confs,
            'MOI': mois,
            'MOP': mops,
            'Penetrance': pens,
            'Gene justification': gene_reasons,
            'Transcript justification': trans_reasons,})

        return gene_df


    def create_region_df(self, panel_dicts):
        """ Create a dataframe of genes covered by the clinical
        indication's current panels.

        args:
            panel_dicts [list of dicts]

        returns:
            region_df [pandas dataframe]
        """

        # initialise df columns

        names = []
        types = []
        var_types = []
        chroms = []
        starts= []
        ends = []
        confs = []
        mois = []
        mops = []
        pens = []
        haplos = []
        triplos = []
        overlaps = []
        reasons = []

        # populate columns

        for panel in panel_dicts:
            for region in panel['regions']:

                names.append(region['name'])
                types.append(region['type'])
                var_types.append(region['var_type'])
                chroms.append(region['chrom'])
                starts.append(region['start'])
                ends.append(region['end'])
                confs.append(region['conf'])
                mois.append(region['moi'])
                mops.append(region['mop'])
                pens.append(region['pen'])
                haplos.append(region['haplo'])
                triplos.append(region['triplo'])
                overlaps.append(region['overlap'])
                reasons.append(region['reason'])

        # create df

        region_df = pd.DataFrame({
            'Region name': names,
            'Type': types,
            'Variant type': var_types,
            'Chromosome': chroms,
            'Start': starts,
            'End': ends,
            'Confidence': confs,
            'MOI': mois,
            'MOP': mops,
            'Penetrance': pens,
            'Haploins.': haplos,
            'Triplosens.': triplos,
            'Overlap': overlaps,
            'Justification': reasons,})

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
            'HGNC ID': ['e.g. 236',
            'Insert data for one gene per row - add more rows as required'],
            'Transcript': ['e.g. NM_183357.3', ''],
            'Confidence': ['e.g. 3', ''],
            'MOI': ['e.g. BIALLELIC, autosomal or pseudoautosomal', ''],
            'MOP': ['e.g. gain-of-function', ''],
            'Penetrance': ['e.g. Complete', ''],
            'Gene justification': ['e.g. PanelApp', ''],
            'Transcript justification': ['e.g. MANE', ''],})

        region_df = pd.DataFrame({
            'Region name': ['e.g. Xp11.23 region (includes MAOA and MAOB) Loss',
            'Insert data for one region per row - add more rows as required'],
            'Type': ['e.g. cnv', ''],
            'Variant type': ['e.g. cnv_loss', ''],
            'Chromosome': ['e.g. X', ''],
            'Start': ['e.g. 43654906', ''],
            'End': ['e.g. 43882474', ''],
            'Confidence': ['e.g. 3', ''],
            'MOI': ['e.g. MONOALLELIC, autosomal or pseudoautosomal', ''],
            'MOP': ['e.g. gain-of-function', ''],
            'Penetrance': ['e.g. Incomplete', ''],
            'Haploins.': ['e.g. 3', ''],
            'Triplosens.': ['e.g. 2', ''],
            'Overlap': ['N/A', ''],
            'Justification': ['e.g. PanelApp', ''],})

        return gene_df, region_df


    def append_df(self, filename, df):

        # get current file contents as a df
        existing_file = pd.read_excel(filename)

        # concatenate new df to existing df
        new_file = pd.concat([existing_file, df], ignore_index=True)

        # write the combination back out to the same filename
        new_file.to_excel(filename, index=False)


    def write_blank_form(self, filename, head_df, gene_df, region_df):
        """ Construct a blank request form as an Excel file. This will
        be returned if there are no panels currently associated with the
        specified clinical indication in the database.

        args:
            filename [str]: for output request form
            head_df [pandas dataframe]: general info about request
            gene_df [pandas dataframe]: all genes covered by these panels
            region_df [pandas dataframe]: all regions covered by these panels

        returns:
            filename [str]
        """

        writer = pd.ExcelWriter(filename, engine='xlsxwriter')

        # write header df in cell A1

        row = 0
        col = 0

        head_df.to_excel(
            writer,
            sheet_name = 'Sheet1',
            startrow = row,
            startcol = col,
            header = False)

        # header df has 5 rows > go to A7 and insert blank gene df

        row += 6

        gene_df.to_excel(
            writer,
            sheet_name = 'Sheet1',
            startrow = row,
            startcol = col,
            index = False)

        # blank gene df has 3 rows > go to A11 and insert blank region df

        row += 4

        region_df.to_excel(
            writer,
            sheet_name = 'Sheet1',
            startrow = row,
            startcol = col,
            index = False)

        writer.save()


    def write_data(self, filename, head_df, panel_df, gene_df, region_df):
        """ Construct the request form as an Excel file.

        args:
            filename [str]: for output request form
            head_df [pandas dataframe]: general info about request
            panel_df [pandas dataframe]: list of current panels for this CI
            gene_df [pandas dataframe]: all genes covered by these panels
            region_df [pandas dataframe]: all regions covered by these panels

        returns:
            filename [str]
        """

        writer = pd.ExcelWriter(filename, engine='xlsxwriter')

        # write header df in cell A1

        row = 0
        col = 0

        head_df.to_excel(
            writer,
            sheet_name = 'Sheet1',
            startrow = row,
            startcol = col,
            header = False)

        # header df has 5 rows > go to A7 and insert panel df

        row += 6

        panel_df.to_excel(
            writer,
            sheet_name = 'Sheet1',
            startrow = row,
            startcol = col,
            index = False)

        # increment row by number of panels

        for df_row in panel_df.iterrows():
            row += 1

        # insert gene df

        row += 2

        gene_df.to_excel(
            writer,
            sheet_name = 'Sheet1',
            startrow = row,
            startcol = col,
            index = False)

        # increment row by number of genes

        for df_row in gene_df.iterrows():
            row += 1

        # insert region df

        row += 2

        region_df.to_excel(
            writer,
            sheet_name = 'Sheet1',
            startrow = row,
            startcol = col,
            index = False)

        writer.save()


    def handle(self, *args, **kwargs):
        """ Execute the functions to create a request form """

        # read in arguments (all are required)

        if (kwargs['req_date']) and \
            (kwargs['requester']) and \
            (kwargs['ci_code']) and \
            (kwargs['ref_genome']):

            req_date = kwargs['req_date'][0]
            requester = kwargs['requester'][0]
            ci_code = kwargs['ci_code'][0]
            ref_genome = kwargs['ref_genome'][0]

            # get records for panels currently linked to that CI code

            panel_records = self.get_panel_records(ci_code, ref_genome)

            # Construct a df of general info about the request

            head_df = self.create_head_df(
                req_date,
                requester,
                ci_code,
                ref_genome)

            if len(panel_records) == 0:

                print('\nNo panels are currently associated with this ' \
                    'clinical indication.\n\n')

                # define blank gene/region tables

                gene_df, region_df = self.create_blank_dfs()

                # write a blank form

                filename = '{}_request_form_{}_NO_PANELS.xlsx'.format(
                    req_date,
                    ci_code)

                output_file = self.write_blank_form(
                    filename,
                    head_df,
                    gene_df,
                    region_df)

            else:
                # get genes and regions for each panel

                panel_dicts = self.retrieve_panel_entities(
                    ref_genome,
                    panel_records)

                # create dataframes

                panel_df = self.create_panel_df(panel_dicts)
                gene_df = self.create_gene_df(panel_dicts)
                region_df = self.create_region_df(panel_dicts)

                # construct the request form and print the filename

                filename = '{}_request_form_{}.xlsx'.format(
                    req_date,
                    ci_code)

                output_file = self.write_data(
                    filename,
                    head_df,
                    panel_df,
                    gene_df,
                    region_df)

            print('Request form created: {}'.format(filename))

        else:
            print("Arguments must be specified in this order: " \
                "request_date, requester, ci_code, ref_genome.\n" \
                "Valid values for ref_genome are GRCh37 and GRCh38.")
