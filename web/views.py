import secrets
import string
import collections
import json
from itertools import chain
import dxpy as dx
import datetime as dt

from django.shortcuts import render, redirect
from django.db.models import QuerySet, Q
from django.db import transaction

from .forms import ClinicalIndicationForm, PanelForm, GeneForm
from .utils.utils import Genepanel

from requests_app.management.commands.history import History
from requests_app.management.commands.utils import parse_hgnc, normalize_version
from core.settings import HGNC_IDS_TO_OMIT
from requests_app.management.commands._insert_ci import insert_test_directory_data

from requests_app.models import (
    ClinicalIndication,
    Panel,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
    ClinicalIndicationTestMethodHistory,
    PanelGene,
    PanelGeneHistory,
    Transcript,
    Gene,
    Confidence,
    ModeOfInheritance,
    ModeOfPathogenicity,
    Penetrance,
)


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

    # normalize panel version
    for panel in all_panels:
        panel.panel_version = normalize_version(panel.panel_version)

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
    try:
        panel: Panel = Panel.objects.get(id=panel_id)
    except Panel.DoesNotExist:
        return render(
            request,
            "web/info/panel.html",
            {
                "panel": None,
                "ci_panels": [],
                "cis": [],
                "ci_history": [],
                "pgs": [],
                "transcripts": [],
                "panel_pending_approval": None,
                "ci_panel_pending_approval": None,
            },
        )

    panel.panel_version = (
        normalize_version(panel.panel_version) if panel.panel_version else None
    )

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
            "active",
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
    try:
        ci: ClinicalIndication = ClinicalIndication.objects.get(id=ci_id)
    except ClinicalIndication.DoesNotExist:
        return render(
            request,
            "web/info/clinical.html",
            {
                "ci": None,
                "ci_panels": [],
                "panels": [],
                "ci_history": [],
                "panel_genes": {},
                "transcripts": [],
                "ci_pending_approval": None,
                "ci_panel_pending_approval": None,
            },
        )

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

    active_panel_ids = [
        cip["panel_id"]
        for cip in ci_panels
        if cip["current"] == True and cip["pending"] == False
    ]

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
    ] = ClinicalIndicationTestMethodHistory.objects.filter(
        clinical_indication_id=ci_id
    ).order_by(
        "-id"
    )

    # combine ci-panels history and ci-test-method history
    agg_history = list(chain(ci_test_method_history, ci_panels_history))

    # fetch panel-gene
    panel_genes: QuerySet[dict] = (
        PanelGene.objects.filter(
            panel_id__in=[p.id for p in panels if p.id in active_panel_ids]
        )
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
    genes = Gene.objects.all().order_by("hgnc_id")

    if request.method == "GET":
        return render(request, "web/addition/add_panel.html", {"genes": genes})
    else:  # POST
        # form submission
        external_id: str = request.POST.get("external_id", "")
        panel_name: str = request.POST.get("panel_name", "")
        panel_version: str = request.POST.get("panel_version", "")

        selected_genes = request.POST.getlist("genes")

        form = PanelForm(request.POST)
        # check form valid
        form_valid: bool = form.is_valid()

        if form_valid:
            # if valid, create Panel
            panel: Panel = Panel.objects.create(
                external_id=request.POST.get("external_id"),
                panel_name=request.POST.get("panel_name"),
                panel_version=request.POST.get("panel_version"),
                pending=True,
                custom=True,
                panel_source="online",
            )

            conf, _ = Confidence.objects.get_or_create(confidence_level=None)
            moi, _ = ModeOfInheritance.objects.get_or_create(mode_of_inheritance=None)
            mop, _ = ModeOfPathogenicity.objects.get_or_create(
                mode_of_pathogenicity=None
            )
            penetrance, _ = Penetrance.objects.get_or_create(penetrance=None)

            for gene_id in selected_genes:
                pg_instance, pg_created = PanelGene.objects.get_or_create(
                    panel_id=panel.id,
                    gene_id=gene_id,
                    active=True,
                    defaults={
                        "confidence_id": conf.id,
                        "moi_id": moi.id,
                        "mop_id": mop.id,
                        "penetrance_id": penetrance.id,
                        "justification": "online",
                    },
                )

                if pg_created:
                    PanelGeneHistory.objects.create(
                        panel_gene_id=pg_instance.id,
                        note=History.panel_gene_created(),
                        user="online",
                    )

            # success, clear form input
            panel_name = ""
            panel_version = ""
            external_id = ""
        else:
            # if invalid, fetch panel from db
            try:
                panel = Panel.objects.get(panel_name__iexact=panel_name)
            except Panel.DoesNotExist:
                pass

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
                "genes": genes,
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
        panels: QuerySet[Panel] = (
            Panel.objects.filter(pending=False).all().order_by("panel_name")
        )

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


def _get_clinical_indication_panel_history() -> (
    QuerySet[ClinicalIndicationPanelHistory]
):
    """
    Function to fetch clinical indication panel history with limit

    Args:
        limit (int): limit of history to fetch
    """

    return (
        ClinicalIndicationPanelHistory.objects.order_by("-created")
        .all()
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


def history(request):
    """
    History page for clinical indication, panel, clinical indication-panel etc.
    """

    if request.method == "GET":
        cip_histories = _get_clinical_indication_panel_history()

        # normalize panel version
        for cip in cip_histories:
            cip[
                "clinical_indication_panel_id__panel_id__panel_version"
            ] = normalize_version(
                cip["clinical_indication_panel_id__panel_id__panel_version"]
            )

        return render(
            request,
            "web/history.html",
            {
                "data": cip_histories,
                "showing": "Clinical Indication Panel",
                "selected": "clinical indication-panel",
            },
        )
    else:
        # POST method
        history_selection = request.POST.get("history selection")

        if history_selection == "panels":
            panels = Panel.objects.all()

            for panel in panels:
                panel.panel_version = normalize_version(panel.panel_version)

            return render(
                request,
                "web/history.html",
                {
                    "data": panels,
                    "showing": "Panels",
                    "selected": "panels",
                },
            )
        elif history_selection == "clinical indications":
            clinical_indications = ClinicalIndication.objects.all()

            return render(
                request,
                "web/history.html",
                {
                    "data": clinical_indications,
                    "showing": "Clinical Indications",
                    "selected": "clinical indications",
                },
            )
        elif history_selection == "clinical indication-panel":
            actions = request.POST.getlist("checkbox selections")

            # if no checkbox ticked, fetch default history limit 50
            if not actions:
                cip_histories = _get_clinical_indication_panel_history()
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
                    "data": cip_histories,
                    "showing": f"Clinical Indication Panel & {' + '.join([action.title() for action in actions])}"
                    if actions
                    else "Clinical Indication Panel",
                    "selected": "clinical indication-panel",
                },
            )
        elif history_selection == "panel-gene":
            panel_genes = PanelGeneHistory.objects.values(
                "created",
                "note",
                "user",
                "panel_gene_id__panel_id__panel_name",
                "panel_gene_id__panel_id",
                "panel_gene_id__gene_id",
                "panel_gene_id__gene_id__hgnc_id",
            )

            return render(
                request,
                "web/history.html",
                {
                    "data": panel_genes,
                    "showing": "Panel Genes",
                    "selected": "panel-gene",
                },
            )


def _generate_random_characters(length: int) -> str:
    return "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for i in range(length)
    )


def edit_gene(request, panel_id: int):
    """
    Edit Panel gene page, the page where you make custom panel from an existing Panel

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
                        active=True,
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

    unique_r_codes: set[str] = set()

    # normalize panel and test directory version
    for cip in cips:
        cip["td_version"] = normalize_version(cip["td_version"])
        cip["panel_id__panel_version"] = normalize_version(
            cip["panel_id__panel_version"]
        )

        r_code = cip["clinical_indication_id__r_code"]
        current = cip["current"]

        # clinical indication - panel is active but another active
        # same clinical indication - panel link also exists
        if current:
            if r_code in unique_r_codes:  # duplicate
                cip["duplicate"] = True
            else:
                # keep a record of all unique clinical indication - panel link
                unique_r_codes.add(r_code)

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

        if action == "deactivate":
            with transaction.atomic():
                ci = ClinicalIndicationPanel.objects.get(id=cip_id)
                ci.current = False
                ci.pending = True
                ci.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=ci.id,
                    user="online",
                    note=History.clinical_indication_panel_deactivated(
                        ci.clinical_indication,
                        ci.panel,
                    ),
                )

        elif action == "activate":
            with transaction.atomic():
                ci = ClinicalIndicationPanel.objects.get(id=cip_id)
                ci.current = True
                ci.pending = True
                ci.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=ci.id,
                    user="online",
                    note=History.clinical_indication_panel_activated(
                        ci.clinical_indication,
                        ci.panel,
                    ),
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

    action_cip = None
    action_panel = None
    action_ci = None
    action_pg = None

    approve_bool = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "approve_ci":
            # this will be called when approving new clinical indication
            clinical_indication_id = request.POST.get("ci_id")

            clinical_indication = ClinicalIndication.objects.get(
                id=clinical_indication_id
            )

            clinical_indication.pending = False
            clinical_indication.save()

            action_ci = clinical_indication
            approve_bool = True

        elif action == "remove_ci":
            # this will be called when removing new clinical indication request
            clinical_indication_id = request.POST.get("ci_id")
            test_method = request.POST.get("test_method") == "true"

            if test_method:
                # called when reverting test method change

                indication_history = (
                    ClinicalIndicationTestMethodHistory.objects.filter(
                        clinical_indication_id=clinical_indication_id,
                    )
                    .order_by("-id")
                    .first()
                )

                # extract test method from "ClinicalIndication metadata test_method changed from Single gene sequencing >=10 amplicons to Small panel"
                previous_test_method = (
                    indication_history.note.split("to")[0].split("from")[-1].strip()
                )

                with transaction.atomic():
                    clinical_indication = ClinicalIndication.objects.get(
                        id=clinical_indication_id,
                    )

                    ClinicalIndicationTestMethodHistory.objects.create(
                        clinical_indication_id=clinical_indication_id,
                        user="online",
                        note=History.clinical_indication_metadata_changed(
                            "test_method",
                            clinical_indication.test_method,
                            previous_test_method,
                        ),
                    )

                    clinical_indication.pending = False
                    clinical_indication.test_method = previous_test_method
                    clinical_indication.save()
            else:
                # remove clinical indication action
                ClinicalIndication.objects.get(id=clinical_indication_id).delete()

                action_ci = True
                approve_bool = False

        elif action == "approve_panel":
            # this will be called when approving new panel
            panel_id = request.POST.get("panel_id")

            panel = Panel.objects.get(id=panel_id)
            panel.pending = False
            panel.save()

            action_panel = panel
            approve_bool = True

        elif action == "remove_panel":
            # this will be called when removing new panel request
            panel_id = request.POST.get("panel_id")

            Panel.objects.get(id=panel_id).delete()

            action_panel = True
            approve_bool = False

        elif action == "approve_cip":
            # `current` is already set to desired outcome
            # this action is purely removing the `pending` label

            # this action is called when approving either new ci-panel link
            # or approving a change to existing ci-panel link
            clinical_indication_panel_id = request.POST.get("cip_id")

            with transaction.atomic():
                clinical_indication_panel = ClinicalIndicationPanel.objects.get(
                    id=clinical_indication_panel_id
                )

                clinical_indication_panel.pending = False
                clinical_indication_panel.save()

                # record in history table
                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=clinical_indication_panel_id,
                    note=History.clinical_indication_panel_activated(
                        clinical_indication_panel.clinical_indication,
                        clinical_indication_panel.panel,
                        True,
                    )
                    if clinical_indication_panel.current
                    else History.clinical_indication_panel_deactivated(
                        clinical_indication_panel.clinical_indication,
                        clinical_indication_panel.panel,
                        True,
                    ),
                    user="online",
                )

            # lazy load relevant field for display in front-end notification
            action_cip = ClinicalIndicationPanel.objects.filter(
                id=clinical_indication_panel_id
            ).values(
                "clinical_indication_id__r_code",
                "clinical_indication_id__name",
                "panel_id__panel_name",
                "panel_id__panel_version",
                "clinical_indication_id",
                "panel_id",
            )[
                0
            ]

            action_cip["panel_id__panel_version"] = normalize_version(
                action_cip["panel_id__panel_version"]
            )
            approve_bool = True

        elif action == "revert_cip":
            # this is called when reverting a change to existing ci-panel link
            # e.g. scenario when user submit to deactivate an existing ci-panel link
            # this will revert the change and set the ci-panel link to active / inactive
            # based on the current changed state
            clinical_indication_panel_id = request.POST.get("cip_id")

            with transaction.atomic():
                clinical_indication_panel = ClinicalIndicationPanel.objects.get(
                    id=clinical_indication_panel_id
                )

                clinical_indication_panel.pending = False
                clinical_indication_panel.current = (
                    not clinical_indication_panel.current
                )  # get the opposite of what it currently is
                clinical_indication_panel.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=clinical_indication_panel_id,
                    note=History.clinical_indication_panel_activated(
                        clinical_indication_panel.clinical_indication,
                        clinical_indication_panel.panel,
                        True,
                    )
                    if clinical_indication_panel.current
                    else History.clinical_indication_panel_deactivated(
                        clinical_indication_panel.clinical_indication,
                        clinical_indication_panel.panel,
                        True,
                    ),
                    user="online",
                )

            action_cip = ClinicalIndicationPanel.objects.filter(
                id=clinical_indication_panel_id
            ).values(
                "clinical_indication_id__r_code",
                "clinical_indication_id__name",
                "panel_id__panel_name",
                "panel_id__panel_version",
                "clinical_indication_id",
                "panel_id",
            )[
                0
            ]

            action_cip["panel_id__panel_version"] = normalize_version(
                action_cip["panel_id__panel_version"]
            )
            approve_bool = False

        elif action == "approve_pg":
            # this is called when approving new panel gene link, either for activation or de-activation
            # depends on what's shown in the front-end

            # we then record the action in history table
            # 1. panel gene approved through manual review
            # 2. panel gene metadata changed (active)
            panel_gene_id = request.POST.get("pg_id")

            with transaction.atomic():
                panel_gene = PanelGene.objects.get(id=panel_gene_id)
                panel_gene.pending = False
                panel_gene.save()

                PanelGeneHistory.objects.create(
                    panel_gene_id=panel_gene_id,
                    note=History.panel_gene_approved("manual review"),
                )

                PanelGeneHistory.objects.create(
                    panel_gene_id=panel_gene_id,
                    note=History.panel_gene_metadata_changed(
                        "active",
                        not panel_gene.active,
                        panel_gene.active,
                    ),
                    user="online",
                )

            action_pg = (
                PanelGene.objects.filter(id=panel_gene_id)
                .values(
                    "panel_id__panel_name",
                    "gene_id__hgnc_id",
                    "panel_id",
                    "gene_id",
                    "active",
                )
                .first()
            )

        elif action == "revert_pg":
            # this is called when reverting a change to existing panel gene link
            # this can be viewed as the opposite of above statement but the logic is the same in terms of making the panel-gene `pending` False
            # both actions "approve_pg" and "revert_pg" makes the panel-gene link `pending` False
            # however, `revert_pg` reverse the `active` field of a panel-gene link
            # so if the front-end shows "pending deactivation", this function will instead
            # "revert" - making the panel-gene active `True` again
            panel_gene_id = request.POST.get("pg_id")

            with transaction.atomic():
                panel_gene = PanelGene.objects.get(id=panel_gene_id)

                PanelGeneHistory.objects.create(
                    panel_gene_id=panel_gene_id,
                    note=History.panel_gene_reverted("manual review"),
                )

                PanelGeneHistory.objects.create(
                    panel_gene_id=panel_gene_id,
                    note=History.panel_gene_metadata_changed(
                        "active",
                        panel_gene.active,
                        not panel_gene.active,
                    ),
                    user="online",
                )

                panel_gene.active = not panel_gene.active
                panel_gene.pending = False
                panel_gene.save()

            action_pg = (
                PanelGene.objects.filter(id=panel_gene_id)
                .values(
                    "panel_id__panel_name",
                    "gene_id__hgnc_id",
                    "panel_id",
                    "gene_id",
                    "active",
                )
                .first()
            )

    panels: QuerySet[Panel] = Panel.objects.filter(pending=True).all()

    # normalize panel version
    for panel in panels:
        if panel.panel_version:
            panel.panel_version = normalize_version(panel.panel_version)

    clinical_indications: QuerySet[
        ClinicalIndication
    ] = ClinicalIndication.objects.filter(pending=True).all()

    # clinical indication test method history
    if clinical_indications:
        for indication in clinical_indications:
            indication_history = (
                ClinicalIndicationTestMethodHistory.objects.filter(
                    clinical_indication_id=indication.id
                )
                .order_by("-id")
                .first()
            )

            # determine if test method is changed
            # or it's a new clinical indication creation
            indication.reason = indication_history if indication_history else "New"

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
            "id",
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

    panel_gene = PanelGene.objects.filter(pending=True).values(
        "id",
        "panel_id__panel_name",
        "panel_id",
        "gene_id__hgnc_id",
        "gene_id",
        "active",
    )

    for pg in panel_gene:
        pg_history = (
            PanelGeneHistory.objects.filter(panel_gene_id=pg["id"])
            .order_by("-id")
            .first()
        )

        pg["reason"] = pg_history.note if pg_history else "Reason not found"

    return render(
        request,
        "web/review/pending.html",
        {
            "panels": panels,
            "cis": clinical_indications,
            "cips": clinical_indication_panels,
            "panel_gene": panel_gene,
            "action_cip": action_cip,
            "action_ci": action_ci,
            "action_panel": action_panel,
            "action_pg": action_pg,
            "approve_bool": approve_bool,
        },
    )


def gene(request, gene_id: int) -> None:
    """
    Page to view gene information
    - shows all the Panel associated with the gene


    Args:
        gene_id (int): gene id
    """
    try:
        gene = Gene.objects.get(id=gene_id)
    except Gene.DoesNotExist:
        return render(
            request,
            "web/info/gene.html",
            {"gene": None, "panels": [], "transcripts": []},
        )

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
        "active",
    )

    transcripts = Transcript.objects.filter(gene_id=gene_id)

    return render(
        request,
        "web/info/gene.html",
        {"gene": gene, "panels": associated_panels, "transcripts": transcripts},
    )


def genepanel(request):
    """
    Genepanel page where user view R code, clinical indication name
    its associated panels and genes.
    """

    # TODO: hard-coded, will become an upload file in the future
    rnas = parse_hgnc("testing_files/eris/hgnc_dump_20230606_1.txt")

    ci_panels = collections.defaultdict(list)
    panel_genes = collections.defaultdict(list)
    relevant_panels = set()
    success = None

    # if there's no CiPanelAssociation date column, return empty list
    if not ClinicalIndicationPanel.objects.filter(current=True, pending=False).exists():
        return render(request, "web/info/genepanel.html", {"genepanels": []})

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
        panel_id__in=relevant_panels, active=True
    ).values("gene_id__hgnc_id", "gene_id", "panel_id"):
        panel_genes[row["panel_id"]].append((row["gene_id__hgnc_id"], row["gene_id"]))

    list_of_genepanel: list[Genepanel] = []
    ci_panel_to_genes = collections.defaultdict(list)
    file_result: list[list[str]] = []

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

                file_result.append(
                    [
                        f"{r_code}_{ci_name}",
                        f"{panel_dict['panel_id__panel_name']}_{normalize_version(panel_dict['panel_id__panel_version']) if panel_dict['panel_id__panel_version'] else '1.0'}",
                        hgnc,
                    ]
                )

    # make GenePanel class for ease of rendering in front end
    for key, hgncs in ci_panel_to_genes.items():
        r_code, ci_name, panel_name, panel_version = [
            val.strip() for val in key.split("|")
        ]
        list_of_genepanel.append(
            Genepanel(r_code, ci_name, panel_name, panel_version, hgncs)
        )

    list_of_genepanel = sorted(list_of_genepanel, key=lambda x: x.r_code)

    if request.method == "POST":
        project_id = request.POST.get("project_id").strip()
        dnanexus_token = request.POST.get("dnanexus_token").strip()

        try:
            # login dnanexus
            dx.set_security_context(
                {
                    "auth_token_type": "Bearer",
                    "auth_token": dnanexus_token,
                }
            )

            # check dnanexus login
            dx.api.system_whoami()

            # check dnanexus project id
            dx.DXProject(project_id)

            project_metadata: dict = dx.DXProject(project_id).describe()
            project_name: str = project_metadata.get("name", "")

            if project_name.startswith("001") or project_name.startswith("002"):
                return render(
                    request,
                    "web/info/genepanel.html",
                    {
                        "genepanels": list_of_genepanel,
                        "error": "Uploading to 001 or 002 project is not allowed.",
                    },
                )

            # sort result
            file_result = sorted(file_result, key=lambda x: [x[0], x[1], x[2]])

            current_datetime = dt.datetime.today().strftime("%Y%m%d")

            # write result to dnanexus file
            with dx.new_dxfile(
                name=f"{current_datetime}_genepanel.tsv",
                project=project_id,
                media_type="text/plain",
            ) as f:
                for row in file_result:
                    data = "\t".join(row)
                    f.write(f"{data}\n")

        except Exception as e:
            return render(
                request,
                "web/info/genepanel.html",
                {"genepanels": list_of_genepanel, "error": e},
            )

        success = True

    return render(
        request,
        "web/info/genepanel.html",
        {
            "genepanels": list_of_genepanel,
            "success": success,
        },
    )


def genes(request):
    """
    Page that display all genes present in database
    POST request allows adding of custom gene into the database
    """
    genes = Gene.objects.all().order_by("hgnc_id")

    if request.method == "POST":
        # parse submitted form
        form = GeneForm(request.POST)

        if form.is_valid():
            hgnc_id: str = request.POST.get("hgnc_id").strip()
            gene_symbol: str = request.POST.get("gene_symbol").strip()

            # if form valid, create gene
            Gene.objects.create(
                hgnc_id=hgnc_id.upper(),
                gene_symbol=gene_symbol.upper(),
            )

        return render(
            request,
            "web/addition/add_gene.html",
            {
                "genes": genes,
                "errors": form.errors if not form.is_valid() else None,
                "success": hgnc_id if form.is_valid() else None,
            },
        )

    return render(
        request,
        "web/addition/add_gene.html",
        {"genes": genes},
    )


def genetotranscript(request):
    """
    g2t page where user can view all genes and its associated transcripts
    there is a form to allow user to upload g2t to specified dnanexus project
    similar to the one in genepanel page

    """
    success = None

    transcripts = (
        Transcript.objects.order_by("gene_id")
        .all()
        .values("gene_id__hgnc_id", "gene_id", "transcript", "source")
    )

    if request.method == "POST":
        project_id = request.POST.get("project_id").strip()
        dnanexus_token = request.POST.get("dnanexus_token").strip()

        try:
            # login dnanexus
            dx.set_security_context(
                {
                    "auth_token_type": "Bearer",
                    "auth_token": dnanexus_token,
                }
            )

            # check dnanexus login
            dx.api.system_whoami()

            # check dnanexus project id
            dx.DXProject(project_id)

            project_metadata: dict = dx.DXProject(project_id).describe()
            project_name: str = project_metadata.get("name", "")

            if project_name.startswith("001") or project_name.startswith("002"):
                return render(
                    request,
                    "web/info/gene2transcript.html",
                    {
                        "transcripts": transcripts,
                        "error": "Uploading to 001 or 002 project is not allowed.",
                    },
                )

            current_datetime = dt.datetime.today().strftime("%Y%m%d")

            # write result to dnanexus file
            with dx.new_dxfile(
                name=f"{current_datetime}_g2t.tsv",
                project=project_id,
                media_type="text/plain",
            ) as f:
                for row in transcripts:
                    hgnc_id = row["gene_id__hgnc_id"]
                    transcript = row["transcript"]
                    source = row.get("source")

                    data = "\t".join(
                        [hgnc_id, transcript, "clinical" if source else "non-clinical"]
                    )
                    data = "\t".join(
                        [hgnc_id, transcript, "clinical" if source else "non-clinical"]
                    )
                    f.write(f"{data}\n")

        except Exception as e:
            return render(
                request,
                "web/info/gene2transcript.html",
                {"transcripts": transcripts, "error": e},
            )

        success = True

    return render(
        request,
        "web/info/gene2transcript.html",
        {"transcripts": transcripts, "success": success},
    )


def test_directory(request):
    """
    This page allows file upload (test directory json file)
    and will insert the data into the database
    """

    error = None
    success = None

    if request.method == "POST":
        try:
            force_update = request.POST.get("force")
            test_directory_data = json.loads(
                request.FILES.get("td_upload").read().decode()
            )

            insert_test_directory_data(
                test_directory_data, True if force_update else False
            )

            success = True

        except Exception as e:
            error = e

    return render(
        request, "web/info/test_directory.html", {"success": success, "error": error}
    )
