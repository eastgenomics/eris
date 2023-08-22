import re
import csv
import secrets
import string
import pandas as pd
import collections
from itertools import chain
import datetime as dt

from django.shortcuts import render
from django.db.models import QuerySet
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect

from .forms import ClinicalIndicationForm, PanelForm
from requests_app.management.commands.history import History
from requests_app.management.commands.utils import parse_hgnc
from .utils.utils import Genepanel
from panel_requests.settings import HGNC_IDS_TO_OMIT

from requests_app.models import (
    ClinicalIndication,
    Panel,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
    ClinicalIndicationTestMethodHistory,
    PanelGene,
    PanelGeneHistory,
    Transcript,
    PanelGeneTranscript,
    Gene,
    Confidence,
    ModeOfInheritance,
    ModeOfPathogenicity,
    Penetrance,
)

from requests_app.management.commands.utils import normalize_version


def index(request):
    """
    Main page. Display all clinical indications and panels
    """

    # fetch all clinical indications
    all_ci: list[ClinicalIndication] = ClinicalIndication.objects.order_by(
        "r_code"
    ).all()

    # fetch all panels
    all_panels: list[dict] = Panel.objects.order_by("panel_name").all()

    return render(
        request,
        "web/index.html",
        {
            "cis": all_ci,
            "panels": all_panels,
        },
    )


def panel(request, panel_id: int):
    """
    Panel info page when viewing single panel
    Shows everything about a panel: genes, transcripts, clinical indications, clinical indication-panel links etc

    Args:
        panel_id (int): panel id
    """

    # fetch panel
    panel: Panel = Panel.objects.get(id=panel_id)
    panel.panel_version = normalize_version(panel.panel_version)

    # fetch ci-panels (related ci)
    ci_panels: QuerySet[
        ClinicalIndicationPanel
    ] = ClinicalIndicationPanel.objects.filter(
        panel_id=panel.id,
    )

    # converting ci-panel version to readable format
    for cip in ci_panels:
        cip.td_version = normalize_version(cip.td_version)

    # fetch associated cis
    cis: QuerySet[ClinicalIndication] = ClinicalIndication.objects.filter(
        id__in=[cp.clinical_indication_id for cp in ci_panels],
    )

    # fetch ci-panels history
    ci_panels_history: QuerySet[
        ClinicalIndicationPanelHistory
    ] = ClinicalIndicationPanelHistory.objects.filter(
        clinical_indication_panel_id__in=[cp.id for cp in ci_panels]
    ).order_by(
        "-id"
    )

    # fetch ci-test-method history
    ci_test_method_history: QuerySet[
        ClinicalIndicationTestMethodHistory
    ] = ClinicalIndicationTestMethodHistory.objects.filter(
        clinical_indication_id__in=[c.id for c in cis],
    )

    # combine ci-panels history and ci-test-method history
    agg_history = list(chain(ci_test_method_history, ci_panels_history))

    # fetch genes associated with panel
    pgs: QuerySet[dict] = (
        PanelGene.objects.filter(panel_id=panel_id)
        .values(
            "gene_id",
            "gene_id__hgnc_id",
            "gene_id__gene_symbol",
        )
        .order_by("gene_id__gene_symbol")
    )

    # fetch all transcripts associated with genes in panel
    all_transcripts: QuerySet[Transcript] = (
        Transcript.objects.filter(gene_id__in=[p["gene_id"] for p in pgs])
        .values("gene_id__hgnc_id", "transcript", "source")
        .order_by("gene_id__hgnc_id", "source")
    )

    return render(
        request,
        "web/info/panel.html",
        {
            "panel": panel,
            "ci_panels": ci_panels,
            "cis": cis,
            "ci_history": agg_history,
            "pgs": pgs,
            "transcripts": all_transcripts,
            "panel_pending_approval": panel.pending,
            "ci_panel_pending_approval": any([cp.pending for cp in ci_panels]),
        },
    )


def clinical_indication(request, ci_id: int):
    """
    Clinical indication info page
    Shows everything about a clinical indication: genes, transcripts, panels, clinical indication-panel links etc

    Args:
        ci_id (int): clinical indication id
    """

    # fetch ci
    ci: ClinicalIndication = ClinicalIndication.objects.get(id=ci_id)

    # fetch ci-panels
    # might have multiple panels but only one active
    ci_panels: QuerySet[ClinicalIndicationPanel] = (
        ClinicalIndicationPanel.objects.filter(
            clinical_indication_id=ci_id,
        )
        .values(
            "id",
            "current",
            "pending",
            "config_source",
            "td_version",
            "created",
            "last_updated",
            "clinical_indication_id",
            "panel_id",
            "panel_id__panel_name",
        )
        .order_by("-pending")
    )

    # converting version to readable format
    for cip in ci_panels:
        cip["td_version"] = normalize_version(cip["td_version"])

    # fetch panels
    # there might be multiple panels due to multiple ci-panel links
    panels: QuerySet[Panel] = Panel.objects.filter(
        id__in=[cp["panel_id"] for cp in ci_panels]
    )

    # fetch ci-panels history
    ci_panels_history: QuerySet[
        ClinicalIndicationPanelHistory
    ] = ClinicalIndicationPanelHistory.objects.filter(
        clinical_indication_panel_id__in=[cp["id"] for cp in ci_panels]
    ).order_by(
        "-id"
    )

    # fetch ci-test-method history
    ci_test_method_history: QuerySet[
        ClinicalIndicationTestMethodHistory
    ] = ClinicalIndicationTestMethodHistory.objects.filter(clinical_indication_id=ci_id)

    # combine ci-panels history and ci-test-method history
    agg_history = list(chain(ci_test_method_history, ci_panels_history))

    # fetch panel-gene
    panel_genes: QuerySet[dict] = (
        PanelGene.objects.filter(panel_id__in=[p.id for p in panels])
        .order_by("panel_id")
        .values(
            "id",
            "panel_id",
            "gene_id",
            "gene_id__hgnc_id",
            "gene_id__gene_symbol",
        )
    )

    # prepare panel-gene dict
    panel_genes_dict: dict[str, list] = collections.defaultdict(list)

    for pg in panel_genes:
        # there can be multiple history associated with a panel-gene id
        latest_pg_history: PanelGeneHistory = (
            PanelGeneHistory.objects.filter(
                panel_gene_id=pg["id"],
            )
            .order_by("-id")
            .first()
        )

        panel_genes_dict[pg["panel_id"]].append(
            {
                "id": pg["id"],
                "gene_id": pg["gene_id"],
                "hgnc": pg["gene_id__hgnc_id"],
                "symbol": pg["gene_id__gene_symbol"],
                "created": latest_pg_history.created,
            }
        )

    # ensure django template can read collections.defaultdict as dict
    panel_genes_dict.default_factory = None

    # fetch all genes associated with panel
    all_gene_ids: set[str] = set([pg["gene_id"] for pg in panel_genes])

    # fetch all transcripts associated with genes in panel
    all_transcripts: QuerySet[Transcript] = (
        Transcript.objects.filter(gene_id__in=all_gene_ids)
        .values("gene_id__hgnc_id", "transcript", "source")
        .order_by("gene_id__hgnc_id", "source")
    )

    return render(
        request,
        "web/info/clinical.html",
        {
            "ci": ci,
            "ci_panels": ci_panels,
            "panels": panels,
            "ci_history": agg_history,
            "panel_genes": panel_genes_dict,
            "transcripts": all_transcripts,
            "ci_pending_approval": ci.pending,
            "ci_panel_pending_approval": any([cp["pending"] for cp in ci_panels]),
        },
    )


def add_clinical_indication(request):
    """
    Add clinical indication page
    """
    if request.method == "GET":
        return render(
            request,
            "web/addition/add_ci.html",
        )
    else:
        # form submission

        # parse form
        form: ClinicalIndicationForm = ClinicalIndicationForm(request.POST)

        # check if form is valid
        form_valid: bool = form.is_valid()

        r_code: str = request.POST.get("r_code").strip()
        name: str = request.POST.get("name").strip()
        test_method: str = request.POST.get("test_method").strip()
        ci = None

        if form_valid:
            # if form valid, add ci to db
            ci_instance, _ = ClinicalIndication.objects.get_or_create(
                r_code=r_code,
                name=name,
                test_method=test_method,
                pending=True,
            )
        else:
            # if form invalid, fetch ci from db
            # return to ask user to modify
            try:
                ci = ClinicalIndication.objects.get(r_code=r_code)
            except ClinicalIndication.DoesNotExist:
                ci = None

        return render(
            request,
            "web/addition/add_ci.html",
            {
                "errors": form.errors if not form_valid else None,
                "success": ci_instance if form_valid else None,
                "r_code": r_code,
                "ci": ci if ci else None,
                "name": name,
                "test_method": test_method,
            },
        )


def add_panel(request):
    """
    Add panel page
    """
    if request.method == "GET":
        return render(
            request,
            "web/addition/add_panel.html",
        )
    else:
        # form submission
        external_id: str = request.POST.get("external_id", "")
        panel_name: str = request.POST.get("panel_name", "")
        panel_version: str = request.POST.get("panel_version", "")

        form: bool = PanelForm(request.POST)
        # check form valid
        form_valid: bool = form.is_valid()

        if form_valid:
            # if valid, create Panel
            panel: Panel = Panel.objects.create(
                external_id=request.POST.get("external_id"),
                panel_name=request.POST.get("panel_name"),
                panel_version=request.POST.get("panel_version"),
                pending=True,
            )
        else:
            # if invalid, fetch panel from db
            try:
                panel = Panel.objects.get(panel_name__iexact=panel_name)
            except Panel.DoesNotExist:
                pass
                # TODO: handle this error

        return render(
            request,
            "web/addition/add_panel.html",
            {
                "panel_name": panel_name,
                "panel_version": panel_version,
                "external_id": external_id,
                "errors": form.errors if not form_valid else None,
                "success": panel if form_valid else None,
                "panel": panel if not form_valid else None,
            },
        )


def add_ci_panel(request, ci_id: int):
    """
    Add clinical indication panel page

    Args:
        ci_id (int): clinical indication id
    """

    # find all panel linked to this ci
    linked_panels: list[int] = [
        cip.panel_id
        for cip in ClinicalIndicationPanel.objects.filter(
            clinical_indication_id=ci_id, current=True
        )
    ]

    # fetch the ci
    clinical_indication: ClinicalIndication = ClinicalIndication.objects.get(id=ci_id)
    # fetch all panels
    panels: QuerySet[Panel] = Panel.objects.all()

    # normalize panel version
    for panel in panels:
        panel.panel_version = normalize_version(panel.panel_version)

    if request.method == "GET":
        # active ci-panel links
        linked_panels: list[int] = [
            cip.panel_id
            for cip in ClinicalIndicationPanel.objects.filter(
                clinical_indication_id=ci_id, current=True
            )
        ]

        # fetch any pending ci-panel links
        pending_ci_panels: list[int] = [
            cip.panel_id
            for cip in ClinicalIndicationPanel.objects.filter(
                clinical_indication_id=ci_id, pending=True
            )
        ]

        # get the ci
        clinical_indication: ClinicalIndication = ClinicalIndication.objects.get(
            id=ci_id
        )

        # only fetch active panels
        panels: QuerySet[Panel] = Panel.objects.filter(pending=False).all()

        # normalize panel version
        for panel in panels:
            panel.panel_version = normalize_version(panel.panel_version)

        return render(
            request,
            "web/addition/add_ci_panel.html",
            {
                "ci": clinical_indication,
                "panels": panels,
                "linked_panels": linked_panels,
                "pending_panels": pending_ci_panels,
            },
        )

    if request.method == "POST":  # form submission
        panel_id: int = request.POST.get("panel_id")
        action: str = request.POST.get("action")

        previous_link = request.META.get("HTTP_REFERER")  # fetch previous link

        if action == "activate":
            # activate ci-panel link
            with transaction.atomic():
                (
                    cip_instance,
                    _,
                ) = ClinicalIndicationPanel.objects.update_or_create(
                    clinical_indication_id=ci_id,
                    panel_id=panel_id,
                    defaults={"current": True, "pending": True},
                )

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip_instance.id,
                    note=History.clinical_indication_panel_activated(ci_id, panel_id),
                    user="online",
                )
        else:
            # deactivate ci-panel link
            with transaction.atomic():
                cip_instance, _ = ClinicalIndicationPanel.objects.update_or_create(
                    clinical_indication_id=ci_id,
                    panel_id=panel_id,
                    defaults={"pending": True, "current": False},
                )

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip_instance.id,
                    note=History.clinical_indication_panel_deactivated(ci_id, panel_id),
                    user="online",
                )

        linked_panels: list[int] = [
            cip.panel_id
            for cip in ClinicalIndicationPanel.objects.filter(
                clinical_indication_id=ci_id, current=True
            )
        ]

        clinical_indication: ClinicalIndication = ClinicalIndication.objects.get(
            id=ci_id
        )
        panels: QuerySet[Panel] = Panel.objects.filter(pending=False).all()

        return redirect(
            previous_link,
            {
                "ci": clinical_indication,
                "panels": panels,
                "linked_panels": linked_panels,
            },
        )


def _get_clinical_indication_panel_history(
    limit: int,
) -> QuerySet[ClinicalIndicationPanelHistory]:
    """
    Function to fetch clinical indication panel history with limit

    Args:
        limit (int): limit of history to fetch
    """

    return ClinicalIndicationPanelHistory.objects.order_by("-created").values(
        "created",
        "note",
        "user",
        "clinical_indication_panel_id__clinical_indication_id__name",
        "clinical_indication_panel_id__clinical_indication_id__r_code",
        "clinical_indication_panel_id__panel_id__panel_name",
        "clinical_indication_panel_id__panel_id__panel_version",
        "clinical_indication_panel_id__clinical_indication_id",
        "clinical_indication_panel_id__panel_id",
    )[:limit]


def history(request):
    """
    Clinical indication panel history page
    """

    limit: int = 50

    if request.method == "GET":
        cip_histories = _get_clinical_indication_panel_history(50)
    else:
        # filter for what checkbox is ticked in the front-end
        actions: list[str] = [
            n
            for n in [
                request.POST.get("deactivated"),
                request.POST.get("created"),
                request.POST.get("changed"),
                request.POST.get("manual review"),
            ]
            if n
        ]

        # if no checkbox ticked, fetch default history limit 50
        if not actions:
            cip_histories = _get_clinical_indication_panel_history(50)
        else:
            # else do cip-history filter with specific query filter
            query_filters = Q()

            for note_prefix in actions:
                query_filters |= Q(note__icontains=note_prefix)

            cip_histories: QuerySet[ClinicalIndicationPanelHistory] = (
                ClinicalIndicationPanelHistory.objects.filter(query_filters)
                .order_by("-created")
                .values(
                    "created",
                    "note",
                    "user",
                    "clinical_indication_panel_id__clinical_indication_id__name",
                    "clinical_indication_panel_id__clinical_indication_id__r_code",
                    "clinical_indication_panel_id__panel_id__panel_name",
                    "clinical_indication_panel_id__panel_id__panel_version",
                    "clinical_indication_panel_id__clinical_indication_id",
                    "clinical_indication_panel_id__panel_id",
                )
            )

            # just to display in front-end on how many rows are fetched
            limit = len(cip_histories)

    # normalize panel version
    for history in cip_histories:
        history[
            "clinical_indication_panel_id__panel_id__panel_version"
        ] = normalize_version(
            history["clinical_indication_panel_id__panel_id__panel_version"]
        )
        
    return render(
        request,
        "web/history.html",
        {
            "cip_histories": cip_histories,
            "selected": request.POST.keys(),
            "limit": limit,
        },
    )


def _generate_random_characters(length: int) -> str:
    return "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for i in range(length)
    )


def edit_gene(request, panel_id: int):
    """
    Edit Panel gene page

    Args:
        panel_id (int): panel id
    """

    # fetch panel and normalize version
    panel: Panel = Panel.objects.get(id=panel_id)
    panel.panel_version = normalize_version(panel.panel_version)

    current_linked_genes = (
        PanelGene.objects.filter(panel_id=panel_id)
        .values(
            "gene_id__gene_symbol",
            "gene_id",
            "gene_id__hgnc_id",
        )
        .order_by("gene_id__hgnc_id")
    )

    all_genes = (
        Gene.objects.all()
        .exclude(id__in=[gene["gene_id"] for gene in current_linked_genes])
        .order_by("hgnc_id")
    )

    if request.method == "POST":
        selected_gene_ids: list[int] = request.POST.getlist("genes")

        if selected_gene_ids:
            with transaction.atomic():
                new_panel = Panel.objects.create(
                    panel_name=f"Custom Panel {_generate_random_characters(5)} based on {panel.panel_name} v{normalize_version(panel.panel_version) if panel.panel_version else 1.0}",
                    panel_source="web",
                    custom=True,
                    pending=True,
                )

                for gene_id in selected_gene_ids:
                    confidence_instance, _ = Confidence.objects.get_or_create(
                        confidence_level=None,  # we only seed level 3 confidence
                    )

                    moi_instance, _ = ModeOfInheritance.objects.get_or_create(
                        mode_of_inheritance=None,
                    )

                    # mop value might be None
                    mop_instance, _ = ModeOfPathogenicity.objects.get_or_create(
                        mode_of_pathogenicity=None
                    )

                    # value for 'penetrance' might be empty
                    penetrance_instance, _ = Penetrance.objects.get_or_create(
                        penetrance=None,
                    )
                    panel_gene_instance = PanelGene.objects.create(
                        panel_id=new_panel.id,
                        gene_id=gene_id,
                        confidence_id=confidence_instance.id,
                        moi_id=moi_instance.id,
                        mop_id=mop_instance.id,
                        penetrance_id=penetrance_instance.id,
                        justification="online",
                    )

                    PanelGeneHistory.objects.create(
                        panel_gene_id=panel_gene_instance.id,
                        note=History.panel_gene_created(),
                        user="Online",
                    )

            # fetch ci-panels (related ci)
            ci_panels: QuerySet[
                ClinicalIndicationPanel
            ] = ClinicalIndicationPanel.objects.filter(
                panel_id=new_panel.id,
            )

            # converting ci-panel version to readable format
            for cip in ci_panels:
                cip.td_version = normalize_version(cip.td_version)

            # fetch associated cis
            cis: QuerySet[ClinicalIndication] = ClinicalIndication.objects.filter(
                id__in=[cp.clinical_indication_id for cp in ci_panels],
            )

            # fetch ci-panels history
            ci_panels_history: QuerySet[
                ClinicalIndicationPanelHistory
            ] = ClinicalIndicationPanelHistory.objects.filter(
                clinical_indication_panel_id__in=[cp.id for cp in ci_panels]
            ).order_by(
                "-id"
            )

            # fetch ci-test-method history
            ci_test_method_history: QuerySet[
                ClinicalIndicationTestMethodHistory
            ] = ClinicalIndicationTestMethodHistory.objects.filter(
                clinical_indication_id__in=[c.id for c in cis],
            )

            # combine ci-panels history and ci-test-method history
            agg_history = list(chain(ci_test_method_history, ci_panels_history))

            # fetch genes associated with panel
            pgs: QuerySet[dict] = (
                PanelGene.objects.filter(panel_id=new_panel.id)
                .values(
                    "gene_id",
                    "gene_id__hgnc_id",
                    "gene_id__gene_symbol",
                )
                .order_by("gene_id__gene_symbol")
            )

            # fetch all transcripts associated with genes in panel
            all_transcripts: QuerySet[Transcript] = (
                Transcript.objects.filter(gene_id__in=[p["gene_id"] for p in pgs])
                .values("gene_id__hgnc_id", "transcript", "source")
                .order_by("gene_id__hgnc_id", "source")
            )

            return render(
                request,
                "web/info/panel.html",
                {
                    "panel": new_panel,
                    "ci_panels": ci_panels,
                    "cis": cis,
                    "ci_history": agg_history,
                    "pgs": pgs,
                    "transcripts": all_transcripts,
                    "panel_pending_approval": new_panel.pending,
                    "ci_panel_pending_approval": any([cp.pending for cp in ci_panels]),
                },
            )
        else:
            # no genes selected, redirect back
            previous_url = request.META.get("HTTP_REFERER")

            return redirect(previous_url)

    return render(
        request,
        "web/edit/edit_panel_gene.html",
        {
            "panel": panel,
            "linked_genes": current_linked_genes,
            "all_genes": all_genes,
        },
    )


def clinical_indication_panels(request):
    """
    Clinical indication panel page

    Shows all clinical indication panel links
    """

    # fetch all ci-panel links
    cips: QuerySet[ClinicalIndicationPanel] = ClinicalIndicationPanel.objects.values(
        "td_version",
        "current",
        "pending",
        "clinical_indication_id",
        "clinical_indication_id__name",
        "clinical_indication_id__r_code",
        "panel_id",
        "panel_id__panel_name",
        "panel_id__panel_version",
        "panel_id__external_id",
        "created",
        "config_source",
    ).order_by("clinical_indication_id__name")

    # normalize panel and test directory version
    for cip in cips:
        cip["td_version"] = normalize_version(cip["td_version"])
        cip["panel_id__panel_version"] = normalize_version(
            cip["panel_id__panel_version"]
        )

    return render(
        request,
        "web/info/clinical_indication_panels.html",
        {
            "cips": cips,
        },
    )


def activate_or_deactivate_clinical_indication_panel(request, cip_id: int) -> None:
    """
    Clinical indication panel add / remove action.
    There is no GET request method for this function.

    Args:
        cip_id (int): clinical indication panel id
    """
    if request.method == "POST":
        previous_link = request.META.get("HTTP_REFERER")  # fetch previous link
        action = request.POST.get("action")

        # TODO: pending for actioned ci-panel should be pending / displayed in front-end
        # for manual review

        if action == "deactivate":
            with transaction.atomic():
                ci = ClinicalIndicationPanel.objects.get(id=cip_id)
                ci.current = False
                ci.pending = True
                ci.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=ci.id,
                    user="web",
                    note="Deactivated by online web",
                )

        elif action == "activate":
            with transaction.atomic():
                ci = ClinicalIndicationPanel.objects.get(id=cip_id)
                ci.current = True
                ci.pending = True
                ci.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=ci.id,
                    user="web",
                    note="Activated by online web",
                )
        else:
            # unknown action, ignore!
            pass

        return redirect(previous_link)


def review(request) -> None:
    """
    Review / Pending page where user can view those links that are
    awaiting approval

    Shows the following pending links:
    - Panel
    - Clinical Indication
    - Clinical Indication Panel
    - PanelGene
    - PanelRegion (TODO)
    - PanelTestMethod (TODO)
    """

    panels: QuerySet[Panel] = Panel.objects.filter(pending=True).all()
    # normalize panel version
    for panel in panels:
        if panel.panel_version:
            panel.panel_version = normalize_version(panel.panel_version)

    clinical_indications: QuerySet[
        ClinicalIndication
    ] = ClinicalIndication.objects.filter(pending=True).all()

    clinical_indication_panels: QuerySet[ClinicalIndicationPanel] = (
        ClinicalIndicationPanel.objects.filter(pending=True)
        .values(
            "clinical_indication_id",
            "clinical_indication_id__name",
            "clinical_indication_id__r_code",
            "panel_id",
            "panel_id__panel_name",
            "panel_id__panel_version",
            "current",
        )
        .order_by("clinical_indication_id__r_code")
    )

    # normalize panel version
    for cip in clinical_indication_panels:
        if cip["panel_id__panel_version"]:
            cip["panel_id__panel_version"] = normalize_version(
                cip["panel_id__panel_version"]
            )
        else:
            cip["panel_id__panel_version"] = 1.0

    panel_genes: QuerySet[PanelGene] = PanelGene.objects.filter(pending=True).values(
        "panel_id__panel_name",
        "panel_id__panel_version",
        "gene_id__hgnc_id",
        "gene_id__gene_symbol",
    )

    return render(
        request,
        "web/review/pending.html",
        {
            "panels": panels,
            "cis": clinical_indications,
            "cips": clinical_indication_panels,
            "pgs": panel_genes,
        },
    )


def gene(request, gene_id: int) -> None:
    """
    Page to view gene information
    - shows all the Panel associated with the gene


    Args:
        gene_id (int): gene id
    """
    gene = Gene.objects.get(id=gene_id)

    associated_panels = PanelGene.objects.filter(gene_id=gene_id).values(
        "panel_id__panel_name",
        "panel_id__panel_version",
        "panel_id",
        "panel_id__external_id",
        "panel_id__panel_source",
        "panel_id__test_directory",
        "panel_id__custom",
        "panel_id__created",
        "panel_id__pending",
    )

    return render(
        request,
        "web/info/gene.html",
        {
            "gene": gene,
            "panels": associated_panels,
        },
    )


def genepanel(request):
    """
    Genepanel page where user view R code, clinical indication name
    its associated panels and genes.
    """

    # TODO: hard-coded, will become an upload file in the future
    rnas = parse_hgnc("testing_files/hgnc_dump_20230606_1.txt")

    ci_panels = collections.defaultdict(list)
    panel_genes = collections.defaultdict(list)
    relevant_panels = set()

    if not ClinicalIndicationPanel.objects.filter(current=True, pending=False).exists():
        # if there's no CiPanelAssociation date column, high chance Test Directory
        # has not been imported yet.
        raise ValueError(
            "Test Directory has yet been imported!"
            "ClinicalIndicationPanel table is empty"
            "python manage.py seed test_dir 220713_RD_TD.json Y"
        )  # TODO: soft fail

    # fetch all relevant clinical indication and panels
    for row in ClinicalIndicationPanel.objects.filter(
        current=True, pending=False
    ).values(
        "clinical_indication_id__r_code",
        "clinical_indication_id__name",
        "panel_id",
        "panel_id__panel_name",
        "panel_id__panel_version",
    ):
        relevant_panels.add(row["panel_id"])
        ci_panels[row["clinical_indication_id__r_code"]].append(row)

    # fetch all relevant genes for the relevant panels
    for row in PanelGene.objects.filter(
        panel_id__in=relevant_panels, pending=False
    ).values("gene_id__hgnc_id", "gene_id", "panel_id"):
        panel_genes[row["panel_id"]].append((row["gene_id__hgnc_id"], row["gene_id"]))

    list_of_genepanel: list[Genepanel] = []
    ci_panel_to_genes = collections.defaultdict(list)

    # for each r code panel combo, we make a list of genes associated with it
    for r_code, panel_list in ci_panels.items():
        # for each clinical indication
        for panel_dict in panel_list:
            # for each panel associated with that clinical indication
            panel_id: str = panel_dict["panel_id"]
            ci_name: str = panel_dict["clinical_indication_id__name"]
            for hgnc, gene_id in panel_genes[panel_id]:
                # for each gene associated with that panel
                if hgnc in HGNC_IDS_TO_OMIT or hgnc in rnas:
                    continue

                unique_key = f"{r_code} | {ci_name} |  {panel_dict['panel_id__panel_name']} | {normalize_version(panel_dict['panel_id__panel_version']) if panel_dict['panel_id__panel_version'] else '1.0'}"

                ci_panel_to_genes[unique_key].append((hgnc, gene_id))

    # make GenePanel class for ease of rendering in front end
    for key, hgncs in ci_panel_to_genes.items():
        r_code, ci_name, panel_name, panel_version = [
            val.strip() for val in key.split("|")
        ]
        list_of_genepanel.append(
            Genepanel(r_code, ci_name, panel_name, panel_version, hgncs)
        )

    return render(request, "web/info/genepanel.html", {"genepanels": list_of_genepanel})
