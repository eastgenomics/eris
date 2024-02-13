#!/usr/bin/env python

from django.db import models, transaction
from functools import wraps
from variant_db.models import *
from panels_backend.models import ReferenceGenome, Panel
from typing import Dict
import logging

# CONSTANTS
ACGS_COLUMNS = [
    "PVS1_verdict",
    "PVS1_evidence",
    "PS1_verdict",
    "PS1_evidence",
    "PS2_verdict",
    "PS2_evidence",
    "PS3_verdict",
    "PS3_evidence",
    "PS4_verdict",
    "PS4_evidence",
    "PM1_verdict",
    "PM1_evidence",
    "PM2_verdict",
    "PM2_evidence",
    "PM3_verdict",
    "PM3_evidence",
    "PM4_verdict",
    "PM4_evidence",
    "PM5_verdict",
    "PM5_evidence",
    "PM6_verdict",
    "PM6_evidence",
    "PP1_verdict",
    "PP1_evidence",
    "PP2_verdict",
    "PP2_evidence",
    "PP3_verdict",
    "PP3_evidence",
    "PP4_verdict",
    "PP4_evidence",
    "BS1_verdict",
    "BS1_evidence",
    "BS2_verdict",
    "BS2_evidence",
    "BS3_verdict",
    "BS3_evidence",
    "BA1_verdict",
    "BA1_evidence",
    "BP2_verdict",
    "BP2_evidence",
    "BP3_verdict",
    "BP3_evidence",
    "BS4_verdict",
    "BS4_evidence",
    "BP1_verdict",
    "BP1_evidence",
    "BP4_verdict",
    "BP4_evidence",
    "BP5_verdict",
    "BP5_evidence",
    "BP7_verdict",
    "BP7_evidence",
]


@transaction.atomic
def insert_row(row_dict: Dict[str, str | int]) -> None:
    """
    Inserts a single row of data into VariantDB

    :param row_dict: dataframe row as dictionary
    """
    sample = _insert_into_table(
        Sample, **_subset_row(row_dict, "instrument_id", "batch_id", "specimen_id")
    )
    testcode = _insert_into_table(TestCode, **_subset_row(row_dict, "test_code"))
    probeset = _insert_into_table(
        ProbeSet, **_subset_row(row_dict, "probeset_id") | {"testcode": testcode}
    )
    affected_status = _insert_into_table(
        AffectedStatus,
        names_to={"affected_status": "name"},
        **_subset_row(row_dict, "affected_status"),
    )
    assertion_criteria = _insert_into_table(
        AssertionCriteria, **_subset_row(row_dict, "category")
    )
    clinical_significance_description = _insert_into_table(
        ClinicalSignificanceDescription, **_subset_row(row_dict, "category")
    )
    assay_method = _insert_into_table(
        AssayMethod,
        names_to={"assay_method": "name"},
        **_subset_row(row_dict, "assay_method"),
    )
    reference_genome = _insert_into_table(
        ReferenceGenome,
        names_to={"ref_genome": "name"},
        **_subset_row(row_dict, "ref_genome"),
    )
    clinvar_collection_method = _insert_into_table(
        ClinvarCollectionMethod,
        names_to={"collection_method": "name"},
        **_subset_row(row_dict, "collection_method"),
    )
    chromosome = _insert_into_table(
        Chromosome, names_to={"chrom": "name"}, **_subset_row(row_dict, "chrom")
    )
    vnt_row_subset = _subset_row(row_dict, "interpreted", "pos", "ref", "alt")
    vnt_row_subset["interpreted"] = vnt_row_subset["interpreted"].lower() == "yes"
    variant = _insert_into_table(
        Variant,
        names_to={"pos": "position"},
        **vnt_row_subset
        | {"reference_genome": reference_genome, "chromosome": chromosome},
    )
    clinvar_allele_origin = _insert_into_table(
        ClinvarAlleleOrigin,
        names_to={"allele_origin": "category"},
        **_subset_row(row_dict, "allele_origin"),
    )
    organisation = _insert_into_table(
        Organization,
        names_to={"organisation": "name"},
        **_subset_row(row_dict, "organisation"),
    )
    institution = _insert_into_table(
        Institution,
        names_to={"institution": "name"},
        **_subset_row(row_dict, "institution"),
    )
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
        "date": row_dict["date"],
    }
    interpretation = _insert_into_table(Interpretation, **interpretation_row)
    # ACGS_CATEGORY_INFORMATION return object is not used, so we throw it away
    _insert_into_table(
        AcgsCategoryInformation,
        **{"interpretation": interpretation} | _subset_row(row_dict, *ACGS_COLUMNS),
    )
    panels = [
        _insert_into_table(
            Panel, **{"panel_name": panel["name"], "panel_version": panel["version"]}
        )
        for panel in row_dict["panels"]
    ]
    # Note that SuperPanel does not currently need to be linked to Interpretation in variantDB;
    # this is because the laboratory does not presently have the option of selecting them in testing.
    for panel in panels:
        _insert_into_table(
            InterpretationPanel, **{"panel": panel, "interpretation": interpretation}
        )

    if not any(_insert_into_table.created):
        logging.warning(
            "Redundant row; this row already exists in the DB. Not inserting..."
        )
    else:
        logging.info("Successfully inserted row")
    # reset decorated function state for next loop.
    # This is being done because it'd just keep filling up with bools otherwise
    _insert_into_table.created = []


def _subset_row(row: Dict[str, str | int], *desired_keys) -> Dict[str, str | int]:
    """
    Subsets a dict given a set of desired keys
    """
    return {k: row[k] for k in desired_keys}


def keep_count_of_truth(f):
    """
    Please note: @wraps is being used to preserve the decorated function's
    metadata. If we didn't use @wraps(f), then the name, docs and so on
    of `f` would change to `keep_count_of_truth`. This is never what we
    want.
    """

    @wraps(f)
    def counted_func(*args, **kwargs):
        inst, created = f(*args, **kwargs)
        counted_func.created.append(created)
        return inst

    counted_func.created = []
    return counted_func


@keep_count_of_truth
def _insert_into_table(
    model_class: models.Model, names_to: dict = None, **kwargs
) -> models.Model:
    """
    Inserts a row of data into a table, given the model

    :param: model_class: The model class to insert data into
    :names_to: names to rename - current name is key, name to use is value.
        Required when the key name doesn't match the corresponding column name in the model
    :kwargs: named arguments to pass in to model for import
    """
    if names_to:
        for k in names_to:
            kwargs = _rename_key(kwargs, k, names_to[k])
    inst, created = model_class.objects.get_or_create(**kwargs)
    return inst, created


def _rename_key(
    dict_obj: Dict[str, str | int], old_name=str, new_name=str
) -> Dict[str, str | int]:
    """
    Rename a dict key
    """
    dict_obj[new_name] = dict_obj[old_name]
    del dict_obj[old_name]
    return dict_obj
