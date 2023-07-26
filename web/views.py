import collections
from itertools import chain

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
)
from requests_app.management.commands._utils import normalize_version


def index(request):
    """
    Main page
    """
    all_ci: list[ClinicalIndication] = ClinicalIndication.objects.order_by(
        "r_code"
    ).all()

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
    Panel info page
    """

    # fetch panel
    panel: Panel = Panel.objects.get(id=panel_id)
    panel.panel_version = normalize_version(panel.panel_version)

    # fetch ci-panels
    ci_panels: QuerySet[
        ClinicalIndicationPanel
    ] = ClinicalIndicationPanel.objects.filter(
        panel_id=panel.id,
    )

    # converting version to readable format
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
        },
    )


def clinical_indication(request, ci_id: int):
    """
    Clinical indication info page
    """

    # fetch ci
    ci: ClinicalIndication = ClinicalIndication.objects.get(id=ci_id)

    # fetch ci-panels
    # might have multiple panels but only one active
    ci_panels: QuerySet[
        ClinicalIndicationPanel
    ] = ClinicalIndicationPanel.objects.filter(clinical_indication_id=ci_id)

    # converting version to readable format
    for cip in ci_panels:
        cip.td_version = normalize_version(cip.td_version)

    # fetch panels
    # there might be multiple panels due to multiple ci-panel links
    panels: QuerySet[Panel] = Panel.objects.filter(
        id__in=[cp.panel_id for cp in ci_panels]
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
                "hgnc": pg["gene_id__hgnc_id"],
                "symbol": pg["gene_id__gene_symbol"],
                "created": latest_pg_history.created_date,
            }
        )

    # ensure django template can read collections.defaultdict as dict
    panel_genes_dict.default_factory = None

    all_gene_ids: set[str] = set([pg["gene_id"] for pg in panel_genes])

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
        },
    )


def add_clinical_indication(request):
    """
    Add clinical indication
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

        form_valid: bool = form.is_valid()

        r_code: str = request.POST.get("r_code").strip()
        name: str = request.POST.get("name").strip()
        test_method: str = request.POST.get("test_method").strip()
        ci = None

        if form_valid:
            ci_instance, _ = ClinicalIndication.objects.get_or_create(
                r_code=r_code,
                name=name,
                test_method=test_method,
            )
        else:
            ci = ClinicalIndication.objects.get(r_code=r_code)

        return render(
            request,
            "web/addition/add_ci.html",
            {
                "errors": form.errors if not form_valid else None,
                "success": ci_instance if form_valid else None,
                "r_code": r_code,
                "ci": ci,
                "name": name,
                "test_method": test_method,
            },
        )


def add_panel(request):
    """
    Add panel
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
        form_valid: bool = form.is_valid()

        if form_valid:
            panel: Panel = Panel.objects.create(
                external_id=request.POST.get("external_id"),
                panel_name=request.POST.get("panel_name"),
                panel_version=request.POST.get("panel_version"),
            )
        else:
            panel = Panel.objects.get(panel_name=panel_name)
            print(form_valid, form.errors, panel)

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
    Add clinical indication panel
    """

    linked_panels: list[int] = [
        cip.panel_id
        for cip in ClinicalIndicationPanel.objects.filter(
            clinical_indication_id=ci_id, current=True
        )
    ]

    clinical_indication: ClinicalIndication = ClinicalIndication.objects.get(id=ci_id)
    panels: QuerySet[Panel] = Panel.objects.all()

    for panel in panels:
        panel.panel_version = normalize_version(panel.panel_version)

    if request.method == "GET":
        return render(
            request,
            "web/addition/add_ci_panel.html",
            {
                "ci": clinical_indication,
                "panels": panels,
                "linked_panels": linked_panels,
            },
        )

    if request.method == "POST":
        panel_id: int = request.POST.get("panel_id")
        action: str = request.POST.get("action")

        previous_link = request.META.get("HTTP_REFERER")  # fetch previous link

        if action == "activate":
            with transaction.atomic():
                cip_instance: ClinicalIndicationPanel = (
                    ClinicalIndicationPanel.objects.update_or_create(
                        clinical_indication_id=ci_id,
                        panel_id=panel_id,
                        current=True,
                    )
                )

                ClinicalIndicationPanelHistory.objects.filter(
                    clinical_indication_panel_id=cip_instance.id,
                    note="Activated by online web",
                )
        else:
            # deactivate
            with transaction.atomic():
                cip_instance: ClinicalIndicationPanel = (
                    ClinicalIndicationPanel.objects.get(
                        clinical_indication_id=ci_id,
                        panel_id=panel_id,
                    )
                )

                cip_instance.current = False
                cip_instance.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip_instance.id,
                    note="Deactivated by online web",
                )

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
        actions: list[str] = [
            n
            for n in [
                request.POST.get("deactivated"),
                request.POST.get("created"),
                request.POST.get("modified"),
            ]
            if n
        ]

        if not actions:
            cip_histories = _get_clinical_indication_panel_history(50)
        else:
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

            limit = len(cip_histories)

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
    """

    # fetch panel and normalize version
    panel: Panel = Panel.objects.get(id=panel_id)
    panel.panel_version = normalize_version(panel.panel_version)

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
    """

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
    if request.method == "POST":
        previous_link = request.META.get("HTTP_REFERER")  # fetch previous link
        action = request.POST.get("action")

        if action == "deactivate":
            with transaction.atomic():
                ci = ClinicalIndicationPanel.objects.get(id=cip_id)
                ci.current = False
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
                ci.save()

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=ci.id,
                    user="web",
                    note="Activated by online web",
                )
        else:
            # unknown action
            pass

        return redirect(previous_link)
