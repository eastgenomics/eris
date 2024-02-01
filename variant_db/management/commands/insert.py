#!/usr/bin/env python

from pandas import DataFrame
from numpy import int64
from django.db import transaction, models
from variant_db.models import *
from panels_backend.models import ReferenceGenome, Panel, PanelSuperPanel
from .utils import subset_row, rename_key

# CONSTANTS
ACGS_COLUMNS = ["PVS1_verdict","PVS1_evidence","PS1_verdict","PS1_evidence","PS2_verdict","PS2_evidence",
                "PS3_verdict","PS3_evidence","PS4_verdict","PS4_evidence","PM1_verdict","PM1_evidence",
                "PM2_verdict","PM2_evidence","PM3_verdict","PM3_evidence","PM4_verdict","PM4_evidence",
                "PM5_verdict","PM5_evidence","PM6_verdict","PM6_evidence","PP1_verdict","PP1_evidence",
                "PP2_verdict","PP2_evidence","PP3_verdict","PP3_evidence","PP4_verdict","PP4_evidence",
                "BS1_verdict","BS1_evidence","BS2_verdict","BS2_evidence","BS3_verdict","BS3_evidence",
                "BA1_verdict","BA1_evidence","BP2_verdict","BP2_evidence","BP3_verdict","BP3_evidence",
                "BS4_verdict","BS4_evidence","BP1_verdict","BP1_evidence","BP4_verdict","BP4_evidence",
                "BP5_verdict","BP5_evidence","BP7_verdict","BP7_evidence"]

def insert_row(row_dict: dict) -> None:
    """
    Function to import stuff into DB

    :param row_dict: dataframe row as dictionary
    """
    sample = insert_into_table(Sample, **subset_row(row_dict, "instrument_id", "batch_id", "specimen_id"))
    testcode = insert_into_table(TestCode, **subset_row(row_dict, "test_code"))
    probeset = insert_into_table(ProbeSet, **subset_row(row_dict, "probeset_id") | {"testcode": testcode})
    affected_status = insert_into_table(AffectedStatus, 
                                        names_to={"affected_status": "name"},
                                        **subset_row(row_dict, "affected_status"))
    assertion_criteria = insert_into_table(AssertionCriteria, **subset_row(row_dict, "category"))
    clinical_significance_description = insert_into_table(ClinicalSignificanceDescription, **subset_row(row_dict, "category"))
    assay_method = insert_into_table(AssayMethod, 
                                     names_to={"assay_method": "name"}, 
                                     **subset_row(row_dict, "assay_method"))
    reference_genome = insert_into_table(ReferenceGenome,
                                         names_to={"ref_genome": "name"}, 
                                         **subset_row(row_dict, "ref_genome"))
    clinvar_collection_method = insert_into_table(ClinvarCollectionMethod, 
                                                  names_to={"collection_method": "name"},
                                                  **subset_row(row_dict, "collection_method"))
    chromosome = insert_into_table(Chromosome, 
                                   names_to={"chrom": "name"}, 
                                   **subset_row(row_dict, "chrom"))
    vnt_row_subset = subset_row(row_dict, "interpreted", "pos", "ref", "alt")
    vnt_row_subset["interpreted"] = vnt_row_subset["interpreted"].lower() == "yes"
    variant = insert_into_table(Variant,
                                names_to={"pos": "position"},
                                **vnt_row_subset | {"reference_genome": reference_genome, "chromosome": chromosome})
    clinvar_allele_origin = insert_into_table(ClinvarAlleleOrigin,
                                              names_to={"allele_origin": "category"},
                                              **subset_row(row_dict, "allele_origin"))
    organisation = insert_into_table(Organization, 
                                     names_to={"organisation": "name"},
                                     **subset_row(row_dict, "organisation"))
    institution = insert_into_table(Institution,
                                    names_to={"institution": "name"},
                                    **subset_row(row_dict, "institution"))

    interpretation_row = {
        "sample": sample,
        "clinical_indication": row_dict["ci"],
        "affected_status": affected_status,
        "assertion_criteria": assertion_criteria,
        "clinical_significance_description": clinical_significance_description,
        "evaluating_organization": organisation,
        "evaluating_institution": institution,
        "assay_method": assay_method,
        "clinvar_collection_method": clinvar_collection_method,
        "variant": variant,
        "clinvar_allele_origin": clinvar_allele_origin,
        "prevalence": row_dict["prevalence"],
        "known_inheritance": row_dict["known_inheritance"],
        "associated_disease": row_dict["associated_disease"],
        "probe_set": probeset,
        "date": row_dict["date"]
    }

    interpretation = insert_into_table(Interpretation, **interpretation_row)

    acgs_category_information = insert_into_table(AcgsCategoryInformation, 
                                                  **{"interpretation": interpretation} | subset_row(row_dict, *ACGS_COLUMNS))
    
    panels = [
        insert_into_table(Panel, **{"panel_name": panel["name"], "panel_version": panel["version"]}) 
        for panel in row_dict["panels"]
    ]

    for panel in panels:
        insert_into_table(InterpretationPanel, **{"panel": panel, "interpretation": interpretation})


def insert_into_table(model_class: models.Model, names_to: dict=None, **kwargs) -> models.Model:
    try:
        for k in names_to:
            kwargs = rename_key(kwargs, k, names_to[k])
    except TypeError:
        pass
    inst = get_or_create(model_class, **kwargs)
    return inst

def get_or_create(model_class, **row):
    inst, _ = model_class.objects.get_or_create(**row)
    return inst