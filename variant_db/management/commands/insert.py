#!/usr/bin/env python

from pandas import DataFrame
from numpy import int64
from django.db import transaction, models
from variant_db.models import *
from panels_backend.models import ReferenceGenome
from .utils import subset_row, rename_key

def insert_row(row_dict: dict) -> None:
    """
    Function to import stuff into DB

    :param row_dict: dataframe row as dictionary
    """
    # subset_row() subsets a dictionary; where objects containing references
    # to foreign tables are needed, the "|" operator (which merges dicts in Python3.9)
    # allows us to pass in objects that aren't in row_dict (like Model objects)
    sample = insert_into_table(Sample, **subset_row(row_dict, "instrument_id", "batch_id", "specimen_id"))
    # TODO: where does test code come from, what type is it
    testcode = insert_into_table(TestCode, **subset_row(row_dict, "test_code"))
    # Here's an example of passing in a Model instance together with workbook entries
    # This will be a common pattern for the rest of this function
    probeset = insert_into_table(ProbeSet, **subset_row(row_dict, "probeset_id") | {"test_code": testcode})
    
    ######
    # TODO: Why is affected status missing from the workbook
    ###### affected_status = insert_into_table(AffectedStatus, **subset_row(row_dict, ""))
    # TODO: Why is assertion criteria missing from the workbook
    ###### assertion_criteria = insert_into_table(AssertionCriteria, **subset_row(row_dict, ""))
    # TODO: Why is clinical significance description missing from the workbook
    ###### clinical_significance_description = insert_into_table(ClinicalSignificanceDescription, **subset_row(row_dict, ""))
    # TODO: Where does assay method come from and why is is missing
    # sometimes we need to rename the keys, which is why this is split into two steps
    # am_row_subset = subset_row(row_dict, "assay_method")
    # am_row_subset = rename_key(row_subset, "assay_method", "name")
    # assay_method = insert_into_table(AssayMethod, **row_subset)
    ######
    # TODO: figure out what happens with things like reference genome where it may already exist. Does get_or_create handle that already?
    # reference_genome = insert_into_table(ReferenceGenome)
    # TODO: figure out where clinvar collection method comes from
    ###### clinvar_collection_method = insert_into_table(ClinvarCollectionMethod, )
    # TODO: The Eris table for this has `panelapp_name` as its only attribute. Resolve this
    ###### chromosome = insert_into_table(Chromosome, **subset_row(row_dict, ""))
    # TODO: figure out issues with reference genome and chromosome models before inserting in Variant
    vnt_row_subset = subset_row(row_dict, "interpreted", "chrom", "pos", "ref", "alt")
    vnt_row_subset = rename_key(row_dict, "pos", "position")
    ###### variant = insert_into_table(Variant, **vnt_row_subset | {"reference_genome_id": reference_genome, "chromosome_id": chromosome})
    # TODO: Clinvar allele origin where
    # clinvar_allele_origin = insert_into_table(ClinvarAlleleOrigin, )
    # TODO: ClinVar submission not in scope yet
    # TODO: hardcode org?
    organisation = insert_into_table(Organization, {name: "Cambridge University Hospitals NHS Foundation Trust"})
    # TODO: hardcode instutition? NUH?
    institution = insert_into_table(Institution, {name: "NHS"})
    # TODO: interpretation
    ###### interpretation code here
    acgs_columns = [k for k in why if re.match("[BP][AMPSV][SV]?\d", row_dict)]
    row_subset = subset_row(row_dict, *acgs_columns)
    # TODO: sort out interpretation
    ###### acgs_category_information = insert_into_table(AcgsCategoryInformation, **{"interpretation": interpretation} | row_subset)


def insert_into_table(cls: models.Model, **kwargs) -> models.Model:
    inst, _ = cls.objects.get_or_create(kwargs)
    return inst