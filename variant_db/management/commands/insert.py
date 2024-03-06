#!/usr/bin/env python

from django.db import models, transaction
from functools import wraps
from variant_db.models import *
from panels_backend.models import ReferenceGenome, Panel
from typing import Callable, TypeVar, ParamSpec
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
def insert_row(row_dict: dict[str, str | int]) -> None:
    """
    Inserts a single row of data into VariantDB

    :param row_dict: dataframe row as dictionary
    """
    sample = _get_or_create(
        Sample,
        **_subset_row(row_dict, "instrument_id", "batch_id", "specimen_id"),
    )
    testcode = _get_or_create(TestCode, **_subset_row(row_dict, "test_code"))
    probeset = _get_or_create(
        ProbeSet,
        **_subset_row(row_dict, "probeset_id") | {"testcode": testcode},
    )
    affected_status = _get_or_create(
        AffectedStatus,
        names_to={"affected_status": "name"},
        **_subset_row(row_dict, "affected_status"),
    )
    assertion_criteria = _get_or_create(
        AssertionCriteria,
        names_to={"assertion_criteria": "category"},
        **_subset_row(row_dict, "assertion_criteria"),
    )
    clinical_significance_description = _get_or_create(
        ClinicalSignificanceDescription,
        names_to={"clinical_significance_description_category": "category"},
        **_subset_row(row_dict, "clinical_significance_description_category"),
    )
    assay_method = _get_or_create(
        AssayMethod,
        names_to={"assay_method": "name"},
        **_subset_row(row_dict, "assay_method"),
    )
    reference_genome = _get_or_create(
        ReferenceGenome,
        names_to={"ref_genome": "name"},
        **_subset_row(row_dict, "ref_genome"),
    )
    clinvar_collection_method = _get_or_create(
        ClinvarCollectionMethod,
        names_to={"collection_method": "name"},
        **_subset_row(row_dict, "collection_method"),
    )
    # chromosome is fetch-only; if the chromosome doesn't exist, crash
    chromosome = _get_or_create(
        Chromosome,
        method="get",
        names_to={"chromosome": "name"},
        **_subset_row(row_dict, "chromosome"),
    )
    vnt_row_subset = _subset_row(row_dict, "interpreted", "start", "reference_allele", "alternate_allele")
    vnt_row_subset["interpreted"] = (
        vnt_row_subset["interpreted"].lower() == "yes"
    )
    variant = _get_or_create(
        Variant,
        **vnt_row_subset
        | {"reference_genome": reference_genome, "chromosome": chromosome},
    )
    clinvar_allele_origin = _get_or_create(
        ClinvarAlleleOrigin,
        names_to={"allele_origin": "category"},
        **_subset_row(row_dict, "allele_origin"),
    )
    organisation = _get_or_create(
        Organization,
        names_to={"organisation": "name", "organisation_id": "external_id"},
        **_subset_row(row_dict, "organisation", "organisation_id"),
    )
    institution = _get_or_create(
        Institution,
        names_to={"institution": "name"},
        **_subset_row(row_dict, "institution"),
    )
    interpretation_row = {
        "sample": sample,
        "preferred_condition_name": row_dict["preferred_condition_name"],
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
        "date_last_evaluated": row_dict["date_last_evaluated"],
    }
    interpretation = _get_or_create(Interpretation, **interpretation_row)
    # ACGS_CATEGORY_INFORMATION return object is not used, so we throw it away
    _get_or_create(
        AcgsCategoryInformation,
        **{"interpretation": interpretation}
        | _subset_row(row_dict, *ACGS_COLUMNS),
    )
    # Panel is fetch-only; if the panel doesn't exist, crash
    panels = [
        _get_or_create(
            Panel,
            method="get",
            **{"panel_name": panel["name"], "panel_version": panel["version"]},
        )
        for panel in row_dict["panels"]
    ]
    # Note that SuperPanel does not currently need to be linked to Interpretation in variantDB;
    # this is because the laboratory does not presently have the option of selecting them in testing.
    for panel in panels:
        _get_or_create(
            InterpretationPanel,
            **{"panel": panel, "interpretation": interpretation},
        )
    clinvar_submission = _get_or_create(
        ClinvarSubmission,
        names_to={"accession_id": "scv_id"},
        **_subset_row(row_dict, "submission_id", "accession_id"),
    )
    if not any(_get_or_create.created):
        logging.warning(
            "Redundant row; this row already exists in the DB. Not inserting..."
        )
    else:
        logging.info("Successfully inserted row")
    # reset decorated function state for next loop.
    # This is being done because it'd just keep filling up with bools otherwise
    _get_or_create.created = []


def _subset_row(
    row: dict[str, str | int], *desired_keys
) -> dict[str, str | int]:
    """
    Subsets a dict given a set of desired keys
    """
    return {k: row[k] for k in desired_keys}


# See docstring in `store_bools` for why these are here
T = TypeVar("T")
P = ParamSpec("P")


def store_bools(func: Callable[P, T]) -> Callable[P, T]:
    """
    This is a decorator that takes a function that returns a `model.Model` and a `bool`,
    and appends the `bool` in a `list` every time it's called. The `bool` objects are
    stored in an internal attribute (`wrapped.created`).

    The type hints for this decorator are misleading, because it only takes
    functions that return a `model.Model` and a `bool` (i.e. `_insert_into_row`).
    However, if we were to do this "properly", the resulting type hint would be
    horrible to write and would actually work against readability.
    The use of `ParamSpec` and `TypeVar` are a suggested convention for
    annotating decorator call signatures (see https://typing.readthedocs.io/en/latest/spec/generics.html#paramspec)

    Please note: @wraps is being used to preserve the decorated function's
    metadata. If we didn't use @wraps(func), then the name, docs and so on
    of `func` would change to `store_bools`, instead of whatever's being
    passed in. This is never what we want.

    :param func: Any function that returns `(models.Model, bool)`
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> models.Model:
        inst, created = func(*args, **kwargs)
        wrapper.created.append(created)
        return inst

    wrapper.created = []
    return wrapper


@store_bools
def _get_or_create(
    model_class: models.Model, method="insert", names_to: dict = None, **kwargs
) -> models.Model:
    """
    Inserts a row of data into a table, given the model

    :param model_class: The model class to insert data into
    :param method: The method to use - only "insert" or "get" are accepted
    :param names_to: names to rename - current name is key, name to use is value.
        Required when the key name doesn't match the corresponding column name in the model
    :kwargs: named arguments to pass in to model for import
    """
    assert method in ("get", "insert")
    if names_to:
        for k in names_to:
            kwargs = _rename_key(kwargs, k, names_to[k])
    if method == "insert":
        inst, created = model_class.objects.get_or_create(**kwargs)
        return inst, created
    elif method == "get":
        # django raises `DoesNotExist` error if missing
        inst = model_class.objects.get(**kwargs)
        return inst, None


def _rename_key(
    dict_obj: dict[str, str | int], old_name=str, new_name=str
) -> dict[str, str | int]:
    """
    Rename a dict key
    """
    dict_obj[new_name] = dict_obj[old_name]
    del dict_obj[old_name]
    return dict_obj
