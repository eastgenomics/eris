import re
import csv
import collections
from itertools import chain
import datetime as dt

from django.shortcuts import render
from django.db.models import QuerySet
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect

from .forms import ClinicalIndicationForm, PanelForm

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
)

from requests_app.management.commands._utils import normalize_version


def _parse_hgnc(file_path) -> set:
    rnas = set()

    with open(file_path, "r") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if re.search("rna", row["Locus type"], re.IGNORECASE) or re.search(
                "mitochondrially encoded",
                row["Approved name"],
                re.IGNORECASE,
            ):
                rnas.add(row["HGNC ID"])

    return rnas


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
            "pending_approval": True if panel.pending else False,
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
    approved_ci_panels: QuerySet[
        ClinicalIndicationPanel
    ] = ClinicalIndicationPanel.objects.filter(
        clinical_indication_id=ci_id, pending=False
    )

    # fetch approved/unapproved ci-panels
    all_ci_panels: QuerySet[ClinicalIndicationPanel] = (
        ClinicalIndicationPanel.objects.filter(
            clinical_indication_id=ci_id,
        )
        .values(
            "id",
            "current",
            "pending",
            "config_source",
            "td_version",
            "created_date",
            "created_time",
            "last_updated",
            "clinical_indication_id",
            "panel_id",
            "panel_id__panel_name",
        )
        .order_by("pending")
    )

    # converting version to readable format
    for cip in approved_ci_panels:
        cip.td_version = normalize_version(cip.td_version)

    # fetch panels
    # there might be multiple panels due to multiple ci-panel links
    panels: QuerySet[Panel] = Panel.objects.filter(
        id__in=[cp.panel_id for cp in approved_ci_panels]
    )

    # fetch ci-panels history
    ci_panels_history: QuerySet[
        ClinicalIndicationPanelHistory
    ] = ClinicalIndicationPanelHistory.objects.filter(
        clinical_indication_panel_id__in=[cp.id for cp in approved_ci_panels]
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
                "created": latest_pg_history.created_date,
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
            "ci_panels": all_ci_panels,
            "panels": panels,
            "ci_history": agg_history,
            "panel_genes": panel_genes_dict,
            "transcripts": all_transcripts,
            "pending_approval": ci.pending,
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
                panel = Panel.objects.get(panel_name=panel_name)
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

        pending_ci_panels: list[int] = [
            cip.panel_id
            for cip in ClinicalIndicationPanel.objects.filter(
                clinical_indication_id=ci_id, pending=True
            )
        ]

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
            with transaction.atomic():
                (
                    cip_instance,
                    _,
                ) = ClinicalIndicationPanel.objects.update_or_create(
                    clinical_indication_id=ci_id,
                    panel_id=panel_id,
                    defaults={
                        "current": False,
                        "pending": True,
                    },
                )

                ci_name: str = ClinicalIndication.objects.get(
                    id=cip_instance.clinical_indication_id
                ).name
                panel_name: str = Panel.objects.get(id=cip_instance.panel_id).panel_name

                ClinicalIndicationPanelHistory.objects.filter(
                    clinical_indication_panel_id=cip_instance.id,
                    note=f"Activated by online web (pending) {ci_name} > {panel_name}",
                )
        else:
            # TODO: to not instantiate action until approval button is clicked?
            # deactivate
            with transaction.atomic():
                cip_instance, _ = ClinicalIndicationPanel.objects.update_or_create(
                    clinical_indication_id=ci_id,
                    panel_id=panel_id,
                    defaults={
                        "pending": True,
                        "current": False,
                    },
                )

                ci_name: str = ClinicalIndication.objects.get(
                    id=cip_instance.clinical_indication_id
                ).name
                panel_name: str = Panel.objects.get(id=cip_instance.panel_id).panel_name

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip_instance.id,
                    note=f"Deactivated by online web (pending) {ci_name} > {panel_name}",
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

    return ClinicalIndicationPanelHistory.objects.order_by(
        "-created_date", "-created_time"
    ).values(
        "created_date",
        "created_time",
        "note",
        "user",
        "clinical_indication_panel_id__clinical_indication_id__name",
        "clinical_indication_panel_id__clinical_indication_id__r_code",
        "clinical_indication_panel_id__panel_id__panel_name",
        "clinical_indication_panel_id__panel_id__panel_version",
    )[
        :limit
    ]


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
                request.POST.get("modified"),
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
                query_filters |= Q(note__startswith=note_prefix)

            cip_histories: QuerySet[ClinicalIndicationPanelHistory] = (
                ClinicalIndicationPanelHistory.objects.filter(query_filters)
                .order_by("-created_date", "-created_time")
                .values(
                    "created_date",
                    "created_time",
                    "note",
                    "user",  # TODO: need clinical indication id and panel id
                    "clinical_indication_panel_id__clinical_indication_id__name",
                    "clinical_indication_panel_id__clinical_indication_id__r_code",
                    "clinical_indication_panel_id__panel_id__panel_name",
                    "clinical_indication_panel_id__panel_id__panel_version",
                    "clinical_indication_panel_id__clinical_indication_id__id",
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


def add_gene(request, panel_id: int):
    """
    Edit Panel gene page

    Args:
        panel_id (int): panel id
    """

    # fetch panel and normalize version
    panel: Panel = Panel.objects.get(id=panel_id)
    panel.panel_version = normalize_version(panel.panel_version)

    # TODO: POST request function not done yet

    return render(
        request,
        "web/addition/add_gene.html",
        {
            "panel": panel,
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
        "clinical_indication_id",
        "clinical_indication_id__name",
        "clinical_indication_id__r_code",
        "panel_id",
        "panel_id__panel_name",
        "panel_id__panel_version",
        "panel_id__external_id",
        "created_date",
        "created_time",
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


def activate_or_deactivate_clinical_indication_panel(request, cip_id: int):
    """
    Clinical indication panel add / remove page

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


def review(request):
    panels: QuerySet[Panel] = Panel.objects.filter(pending=True).all()
    # normalize panel version
    for panel in panels:
        if panel.panel_version:
            panel.panel_version = normalize_version(panel.panel_version)

    cis: QuerySet[ClinicalIndication] = ClinicalIndication.objects.filter(
        pending=True
    ).all()

    cips: QuerySet[ClinicalIndicationPanel] = ClinicalIndicationPanel.objects.filter(
        pending=True
    ).values(
        "clinical_indication_id__name",
        "clinical_indication_id__r_code",
        "panel_id__panel_name",
        "panel_id__panel_version",
    )

    # normalize panel version
    for cip in cips:
        if cip["panel_id__panel_version"]:
            cip["panel_id__panel_version"] = normalize_version(
                cip["panel_id__panel_version"]
            )

    pgs: QuerySet[PanelGene] = PanelGene.objects.filter(pending=True).values(
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
            "cis": cis,
            "cips": cips,
            "pgs": pgs,
        },
    )


def gene(request, gene_id: int):
    gene = Gene.objects.get(id=gene_id)

    associated_panels = PanelGene.objects.filter(gene_id=gene_id).values(
        "panel_id__panel_name",
        "panel_id__panel_version",
        "panel_id",
        "panel_id__external_id",
        "panel_id__panel_source",
        "panel_id__test_directory",
        "panel_id__custom",
        "panel_id__created_date",
        "panel_id__created_time",
        "panel_id__pending",
    )

    print(associated_panels)

    return render(
        request,
        "web/info/gene.html",
        {
            "gene": gene,
            "panels": associated_panels,
        },
    )


def genepanel(request):
    # TODO: hard-coded
    rnas = _parse_hgnc("testing_files/hgnc_dump_20230606_1.txt")

    ci_panels = collections.defaultdict(list)
    panel_genes = collections.defaultdict(list)
    relevant_panels = set()

    results = []

    # start genepanel logic

    if not ClinicalIndicationPanel.objects.filter(current=True, pending=False).exists():
        # if there's no CiPanelAssociation date column, high chance Test Directory
        # has not been imported yet.
        raise ValueError(
            "Test Directory has yet been imported!"
            "ClinicalIndicationPanel table is empty"
            "python manage.py seed test_dir 220713_RD_TD.json Y"
        )  # TODO: soft fail

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

    for row in PanelGene.objects.filter(
        panel_id__in=relevant_panels, pending=False
    ).values("gene_id__hgnc_id", "panel_id"):
        panel_genes[row["panel_id"]].append(row["gene_id__hgnc_id"])

    for r_code, panel_list in ci_panels.items():
        # for each clinical indication
        for panel_dict in panel_list:
            # for each panel associated with that clinical indication
            panel_id: str = panel_dict["panel_id"]
            ci_name: str = panel_dict["clinical_indication_id__name"]
            for hgnc in panel_genes[panel_id]:
                # for each gene associated with that panel
                if hgnc in ["HGNC:12029", "HGNC:5541"] or hgnc in rnas:
                    continue

                results.append(
                    [
                        f"{r_code}_{ci_name}",
                        f"{panel_dict['panel_id__panel_name']}_{normalize_version(panel_dict['panel_id__panel_version']) if panel_dict['panel_id__panel_version'] else '1.0'}",
                        hgnc,
                    ]
                )

    sorted(results, key=lambda x: [x[0], x[1], x[2]])

    # end genepanel logic

    # processing for display in frontend
    ci_panel_to_gene = collections.defaultdict(list)
    for gp in results:
        ci_panel_to_gene[f"{gp[0]}_{gp[1]}"].append(gp[2])

    return render(request, "web/info/genepanel.html", {"genepanels": results})
