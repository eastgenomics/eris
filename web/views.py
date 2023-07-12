import collections
from itertools import chain

from django.shortcuts import render
from django.db.models import QuerySet

from .forms import ClinicalIndicationForm

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
    panel: Panel = Panel.objects.get(id=panel_id)

    return render(
        request,
        "web/panel.html",
        {
            "panel": panel,
        },
    )


def ci(request, ci_id: int):
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
        "created_date"
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
        .values("id", "panel_id", "gene_id", "gene_id__hgnc_id", "gene_id__gene_symbol")
    )

    all_gene_ids: set[str] = set([pg["gene_id"] for pg in panel_genes])

    # prepare panel-gene dict
    panel_genes_dict: dict[str, list] = collections.defaultdict(list)

    for gene in panel_genes:
        pg_history = PanelGeneHistory.objects.get(
            panel_gene_id=gene["id"],
        )
        panel_genes_dict[gene["panel_id"]].append(
            {
                "hgnc": gene["gene_id__hgnc_id"],
                "symbol": gene["gene_id__gene_symbol"],
                "created": pg_history.created_date,
            }
        )

    # ensure django template can read collections.defaultdict as dict
    panel_genes_dict.default_factory = None

    all_transcripts: QuerySet[Transcript] = (
        Transcript.objects.filter(gene_id__in=all_gene_ids)
        .values("gene_id__hgnc_id", "transcript", "source")
        .order_by("gene_id__hgnc_id", "source")
    )

    return render(
        request,
        "web/clinical.html",
        {
            "ci": ci,
            "ci_panels": ci_panels,
            "panels": panels,
            "ci_history": agg_history,
            "panel_genes": panel_genes_dict,
            "transcripts": all_transcripts,
        },
    )


def add_ci_panel(request):
    if request.method == "GET":
        return render(
            request,
            "web/add_ci_panel.html",
        )
    else:
        # form submission
        print(request.POST)

        form: ClinicalIndicationForm = ClinicalIndicationForm(request.POST)

        if form.is_valid():
            r_code: str = request.POST.get("r_code")
            name: str = request.POST.get("name")
            test_method: str = request.POST.get("test_method")

            ci_instance: ClinicalIndication = ClinicalIndication.objects.create(
                r_code=r_code,
                name=name,
                test_method=test_method,
            )
        else:
            errors = form.errors
            print(errors)

        return render(
            request,
            "web/add_ci_panel.html",
            {
                "errors": form.errors if not form.is_valid() else None,
                "success": ci_instance.id if form.is_valid() else None,
            },
        )
