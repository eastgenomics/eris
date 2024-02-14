import collections
import json
import pandas as pd
from io import BytesIO
from panels_backend.management.commands._parse_transcript import (
    check_missing_columns,
)
from itertools import chain
import dxpy as dx
import datetime as dt
from packaging.version import Version
from django.http import HttpRequest, HttpResponse

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db.models import QuerySet, Q, F
from django.db import transaction
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import permission_required


from .forms import ClinicalIndicationForm, PanelForm, GeneForm
from .utils.utils import WebChildPanel, WebGene, WebGenePanel

from panels_backend.management.commands.history import History
from panels_backend.management.commands.utils import (
    normalize_version,
)
from core.settings import HGNC_IDS_TO_OMIT
from panels_backend.management.commands._insert_ci import (
    insert_test_directory_data,
)
from panels_backend.management.commands._parse_transcript import (
    get_latest_transcript_release,
)

from panels_backend.models import (
    ClinicalIndication,
    Panel,
    ClinicalIndicationPanel,
    ClinicalIndicationPanelHistory,
    ClinicalIndicationSuperPanel,
    ClinicalIndicationSuperPanelHistory,
    CiPanelTdRelease,
    CiSuperpanelTdRelease,
    ClinicalIndicationTestMethodHistory,
    PanelGene,
    PanelGeneHistory,
    PanelSuperPanel,
    Gene,
    Confidence,
    ModeOfInheritance,
    ModeOfPathogenicity,
    Penetrance,
    TranscriptReleaseTranscript,
    TestDirectoryRelease,
    SuperPanel,
    TranscriptRelease,
    TranscriptReleaseTranscriptFile,
    TranscriptSource,
    ReferenceGenome,
    Transcript,
)


def index(request: HttpRequest) -> HttpResponse:
    """
    Main page of the web app.
    Displaying:
    - Clinical Indications
    - Panels
    - Clinical Indication-Panel links
    - Test Directory Releases
    - Transcript Sources
    """

    # fetch all clinical indications
    clinical_indications: list[
        ClinicalIndication
    ] = ClinicalIndication.objects.order_by("r_code").all()

    # fetch all panels
    panels: list[Panel] = Panel.objects.order_by("panel_name").all()

    # normalize panel version
    for panel in panels:
        panel.panel_version = normalize_version(panel.panel_version)
        panel.superpanel = False

    super_panels: list[SuperPanel] = SuperPanel.objects.all()

    # normalize panel version
    for sp in super_panels:
        sp.panel_version = normalize_version(sp.panel_version)
        sp.superpanel = True

    all_panels = list(chain(panels, super_panels))

    # fetch clinical indication-panel links
    clinical_indication_panels = ClinicalIndicationPanel.objects.values(
        "clinical_indication_id",
        "panel_id",
        "current",
        "pending",
        "id",
        panel_name=F("panel_id__panel_name"),
        clinical_indication_name=F("clinical_indication_id__name"),
    )

    clinical_indication_sp = ClinicalIndicationSuperPanel.objects.values(
        "clinical_indication_id",
        "current",
        "pending",
        "id",
        panel_id=F("superpanel_id"),
        panel_name=F("superpanel_id__panel_name"),
        clinical_indication_name=F("clinical_indication_id__name"),
    )

    # get latest test directory release for each ci-panel link
    for row in clinical_indication_sp:
        superpanel_id = row["id"]

        releases = CiSuperpanelTdRelease.objects.filter(
            ci_superpanel_id=superpanel_id
        ).values(
            "td_release_id__release",
        )

        row["td_release"] = (
            max(
                [
                    Version(release["td_release_id__release"])
                    for release in releases
                ]
            )
            if releases
            else None
        )

        row["superpanel"] = True

    for row in clinical_indication_panels:
        id = row["id"]

        releases = CiPanelTdRelease.objects.filter(ci_panel_id=id).values(
            "td_release_id__release",
        )

        row["td_release"] = (
            max(
                [
                    Version(release["td_release_id__release"])
                    for release in releases
                ]
            )
            if releases
            else None
        )

        row["superpanel"] = False

    all_clinical_indication_p_and_sp = list(
        chain(clinical_indication_panels, clinical_indication_sp)
    )

    # fetch Test Directory Releases
    td_releases = TestDirectoryRelease.objects.all()

    transcript_sources = TranscriptRelease.objects.values(
        "id",
        "source__source",
        "source",
        "release",
        "created",
        "reference_genome__name",
    ).order_by("-created")

    for ts in transcript_sources:
        # NOTE: HGMD have 2 files (g2refseq and markname)
        ts["files"] = TranscriptReleaseTranscriptFile.objects.filter(
            transcript_release=ts["id"]
        ).values("transcript_file__file_type", "transcript_file__file_id")

    return render(
        request,
        "web/index.html",
        {
            "cis": clinical_indications,
            "panels": all_panels,
            "cips": all_clinical_indication_p_and_sp,
            "td_releases": td_releases,
            "transcript_sources": transcript_sources,
        },
    )


def login(request: HttpRequest):
    """
    Allows logging in
    """
    return render(request, "accounts/login.html")


def logout(request: HttpRequest):
    """
    Allows logging out
    """
    return render(request, "accounts/logout.html")


def panel(request: HttpRequest, panel_id: int) -> HttpResponse:
    """
    Panel info page when viewing single panel
    Shows everything about a panel: genes, transcripts, clinical indications, clinical indication-panel links etc

    Args:
        panel_id (int): panel id
    """

    if request.method == "GET":
        # fetch panel
        try:
            panel: Panel = Panel.objects.get(id=panel_id)
        except Panel.DoesNotExist:
            return render(
                request,
                "web/info/panel.html",
            )

        panel.panel_version = (
            normalize_version(panel.panel_version)
            if panel.panel_version
            else None
        )

        # fetch ci-panels (related ci)
        ci_panels: QuerySet[
            ClinicalIndicationPanel
        ] = ClinicalIndicationPanel.objects.filter(
            panel_id=panel.id,
        ).values(
            "id",
            "current",
            "pending",
            "clinical_indication_id",
            "clinical_indication_id__name",
            "clinical_indication_id__r_code",
        )

        # fetch genes associated with panel
        panel_genes: QuerySet[dict] = (
            PanelGene.objects.filter(panel_id=panel_id)
            .values(
                "gene_id",
                "gene_id__hgnc_id",
                "gene_id__gene_symbol",
                "active",
            )
            .order_by("gene_id__gene_symbol")
        )

        return render(
            request,
            "web/info/panel.html",
            {
                "panel": panel,
                "ci_panels": ci_panels,
                "panel_genes": panel_genes,
            },
        )

    else:
        # POST method (from review)
        action = request.POST.get("action")
        panel = Panel.objects.get(id=panel_id)

        if action == "approve":
            panel.pending = False
            panel.save()

        elif action == "remove":
            panel.delete()

        return redirect("review")


def superpanel(request: HttpRequest, superpanel_id: int) -> HttpResponse:
    # fetch superpanel
    try:
        superpanel = SuperPanel.objects.get(id=superpanel_id)
    except SuperPanel.DoesNotExist:
        return render(
            request,
            "web/info/superpanel.html",
        )

    superpanel.panel_version = (
        normalize_version(superpanel.panel_version)
        if superpanel.panel_version
        else None
    )

    # fetch ci-panels (related ci)
    ci_panels = ClinicalIndicationSuperPanel.objects.filter(
        superpanel_id=superpanel.id,
    ).values(
        "id",
        "current",
        "pending",
        "clinical_indication_id",
        "clinical_indication_id__name",
    )

    child_panels = PanelSuperPanel.objects.filter(
        superpanel_id=superpanel.id
    ).values(
        "panel_id",
        "panel_id__panel_name",
        "panel_id__panel_version",
        "panel_id__external_id",
    )

    for child in child_panels:
        child["panel_id__panel_version"] = normalize_version(
            child["panel_id__panel_version"]
        )

    return render(
        request,
        "web/info/superpanel.html",
        {
            "superpanel": superpanel,
            "cips": ci_panels,
            "child_panels": child_panels,
        },
    )


def clinical_indication(request: HttpRequest, ci_id: int) -> HttpResponse:
    """
    Clinical indication info page
    Shows everything about a clinical indication: genes, transcripts, panels, clinical indication-panel links etc

    Args:
        ci_id (int): clinical indication id
    """
    if request.method == "GET":
        # fetch ci
        try:
            ci: ClinicalIndication = ClinicalIndication.objects.get(id=ci_id)
        except ClinicalIndication.DoesNotExist:
            return render(request, "web/info/clinical_indication.html")

        # fetch ci-panels
        # might have multiple panels but only one active
        ci_panels: QuerySet[
            ClinicalIndicationPanel
        ] = ClinicalIndicationPanel.objects.filter(
            clinical_indication_id=ci_id,
        ).values(
            "id",
            "current",
            "pending",
            "clinical_indication_id",
            "panel_id",
            "panel_id__panel_name",
        )

        ci_superpanels = ClinicalIndicationSuperPanel.objects.filter(
            clinical_indication_id=ci_id
        ).values(
            "id",
            "current",
            "pending",
            "clinical_indication_id",
            "superpanel_id",
            "superpanel_id__panel_name",
        )

        # fetch ci-test-method history
        test_method_history: QuerySet[
            ClinicalIndicationTestMethodHistory
        ] = ClinicalIndicationTestMethodHistory.objects.filter(
            clinical_indication_id=ci_id
        ).order_by(
            "-id"
        )

        return render(
            request,
            "web/info/clinical_indication.html",
            {
                "ci": ci,
                "ci_panels": ci_panels,
                "tm_history": test_method_history,
                "ci_superpanels": ci_superpanels,
            },
        )

    else:
        action = request.POST.get("action")
        ci = ClinicalIndication.objects.get(id=ci_id)

        if action == "approve":
            ci.pending = False
            ci.save()

            return redirect("clinical_indication", ci_id=ci_id)
        elif action == "remove":
            test_method = (
                request.POST.get("test_method") == "true"
            )  # check if it is test method change

            if not test_method:  # if not test method change
                ci.delete()  # ci is newly created, so we can delete it

            else:
                with transaction.atomic():
                    # if test method change, we need to revert it back to previous test method
                    indication_history = (
                        ClinicalIndicationTestMethodHistory.objects.filter(
                            clinical_indication_id=ci_id,
                        )
                        .order_by("-id")
                        .first()
                    )

                    # extract test method from "ClinicalIndication metadata test_method changed from Single gene sequencing >=10 amplicons to Small panel"
                    previous_test_method = (
                        indication_history.note.split("to")[0]
                        .split("from")[-1]
                        .strip()
                    )

                    ClinicalIndicationTestMethodHistory.objects.create(
                        clinical_indication_id=ci_id,
                        note=History.clinical_indication_metadata_changed(
                            "test_method",
                            ci.test_method,
                            previous_test_method,
                        ),
                        user=request.user,
                    )

                    ci.pending = False
                    ci.test_method = previous_test_method
                    ci.save()

            return redirect("review")


@permission_required("staff", raise_exception=False)
def add_clinical_indication(request: HttpRequest) -> HttpResponse:
    """
    Add clinical indication page
    """
    if request.method == "GET":
        return render(
            request,
            "web/addition/add_clinical_indication.html",
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
        clinical_indication = None

        if form_valid:
            # if form valid, add ci to db
            clinical_indication, _ = ClinicalIndication.objects.get_or_create(
                r_code=r_code,
                name=name,
                test_method=test_method,
                defaults={"pending": True},
            )

            return redirect(
                "clinical_indication",
                ci_id=clinical_indication.id,
            )

        else:
            # if form invalid, fetch ci from db
            # return to ask user to modify
            try:
                clinical_indication = ClinicalIndication.objects.get(
                    r_code=r_code
                )
            except ClinicalIndication.DoesNotExist:
                pass

            return render(
                request,
                "web/addition/add_clinical_indication.html",
                {
                    "errors": form.errors if not form_valid else None,
                    "ci": clinical_indication,
                },
            )


@permission_required("staff", raise_exception=False)
def add_panel(request: HttpRequest) -> HttpResponse:
    """
    Add panel page
    """
    genes = Gene.objects.all().order_by("hgnc_id")

    if request.method == "GET":
        return render(request, "web/addition/add_panel.html", {"genes": genes})
    else:  # POST
        # form submission
        panel_name: str = request.POST.get("panel_name", "")

        selected_genes = request.POST.getlist("genes")

        form = PanelForm(request.POST)
        # check form valid
        form_valid: bool = form.is_valid()

        if form_valid:
            with transaction.atomic():
                # if valid, create Panel
                panel: Panel = Panel.objects.create(
                    external_id=form.cleaned_data.get("external_id"),
                    panel_name=form.cleaned_data.get("panel_name"),
                    panel_version=form.cleaned_data.get("panel_version"),
                    pending=True,
                    custom=True,
                    panel_source="online",
                )

                conf, _ = Confidence.objects.get_or_create(
                    confidence_level=None
                )
                moi, _ = ModeOfInheritance.objects.get_or_create(
                    mode_of_inheritance=None
                )
                mop, _ = ModeOfPathogenicity.objects.get_or_create(
                    mode_of_pathogenicity=None
                )
                penetrance, _ = Penetrance.objects.get_or_create(
                    penetrance=None
                )

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
                            user=request.user,
                        )

            return redirect("panel", panel_id=panel.id)
        else:
            # if invalid, fetch panel from db
            try:
                panel = Panel.objects.get(panel_name__iexact=panel_name)
            except Panel.DoesNotExist:
                panel = None

        return render(
            request,
            "web/addition/add_panel.html",
            {
                "panel": panel,
                "genes": genes,
                "errors": form.errors if not form_valid else None,
            },
        )


@permission_required("staff", raise_exception=False)
def add_ci_panel(request: HttpRequest) -> HttpResponse:
    """
    Add clinical indication panel page
    """
    if request.method == "GET":
        clinical_indications = ClinicalIndication.objects.all().order_by(
            "r_code"
        )

        panels = (
            Panel.objects.filter(pending=False)
            .all()
            .order_by("external_id", "panel_name")
        )

        for panel in panels:
            panel.panel_version = (
                normalize_version(panel.panel_version)
                if panel.panel_version
                else ""
            )
            panel.external_id = panel.external_id if panel.external_id else ""

        return render(
            request,
            "web/addition/add_ci_panel.html",
            {
                "cis": clinical_indications,
                "panels": panels,
            },
        )

    else:
        panel_id = request.POST.get("panel")
        clinical_indication_id = request.POST.get("clinical_indication")

        with transaction.atomic():
            (
                cip_instance,
                created,
            ) = ClinicalIndicationPanel.objects.get_or_create(
                clinical_indication_id=clinical_indication_id,
                panel_id=panel_id,
                defaults={
                    "current": True,
                    "pending": True,
                },
            )

            # don't require review if cip already exist and pending is False
            cip_instance.pending = (
                False if (not cip_instance.pending and not created) else True
            )
            cip_instance.save()

            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel_id=cip_instance.id,
                note=History.clinical_indication_panel_created(),
                user=request.user,
            )

        return redirect(
            "clinical_indication_panel",
            cip_id=cip_instance.id,
        )


def _get_clinical_indication_panel_history() -> QuerySet:
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
            "user__username",
            "clinical_indication_panel_id__clinical_indication_id__name",
            "clinical_indication_panel_id__clinical_indication_id__r_code",
            "clinical_indication_panel_id__panel_id__panel_name",
            "clinical_indication_panel_id__panel_id__panel_version",
            "clinical_indication_panel_id__clinical_indication_id",
            "clinical_indication_panel_id__panel_id",
        )
    )


def history(request: HttpRequest) -> HttpResponse:
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
                    ClinicalIndicationPanelHistory.objects.filter(
                        query_filters
                    )
                    .order_by("-created")
                    .values(
                        "created",
                        "note",
                        "user",
                        "user__username",
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
                    history[
                        "clinical_indication_panel_id__panel_id__panel_version"
                    ]
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
                "user__username",
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


def clinical_indication_panel(
    request: HttpRequest, cip_id: str
) -> HttpResponse:
    """
    Clinical indication panel page

    Shows all clinical indication panel links
    """

    if request.method == "GET":
        clinical_indication_panel = (
            ClinicalIndicationPanel.objects.filter(id=cip_id)
            .values(
                "clinical_indication_id__r_code",
                "clinical_indication_id__name",
                "panel_id__panel_name",
                "panel_id__panel_version",
                "panel_id",
                "clinical_indication_id",
                "current",
                "pending",
                "id",
            )
            .first()
        )

        releases = CiPanelTdRelease.objects.filter(
            ci_panel_id=clinical_indication_panel["id"]
        ).values(
            "td_release_id__release",
            "td_release_id__td_source",
            "td_release_id__config_source",
            "td_release_id__td_date",
            "id",
        )

        return render(
            request,
            "web/info/clinical_indication_panel.html",
            {"cip": clinical_indication_panel, "releases": releases},
        )
    elif request.method == "POST":
        action = request.POST.get("action")
        clinical_indication_panel = ClinicalIndicationPanel.objects.get(
            id=cip_id
        )

        with transaction.atomic():
            if action in ["activate", "deactivate"]:
                if action == "activate":
                    clinical_indication_panel.current = True
                    ClinicalIndicationPanelHistory.objects.create(
                        clinical_indication_panel_id=cip_id,
                        note=History.clinical_indication_panel_activated(
                            cip_id, True
                        ),
                        user=request.user,
                    )
                elif action == "deactivate":
                    clinical_indication_panel.current = False
                    ClinicalIndicationPanelHistory.objects.create(
                        clinical_indication_panel_id=cip_id,
                        note=History.clinical_indication_panel_deactivated(
                            cip_id, True
                        ),
                        user=request.user,
                    )
                clinical_indication_panel.pending = (
                    True  # require manual review
                )
            elif action == "revert":
                # action is "revert" from Review page
                clinical_indication_panel.current = (
                    not clinical_indication_panel.current
                )
                clinical_indication_panel.pending = False

                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip_id,
                    note=History.clinical_indication_panel_reverted(
                        id=cip_id,
                        old_value=clinical_indication_panel.current,
                        new_value=not clinical_indication_panel.current,
                        review=True,
                    ),
                    user=request.user,
                )
            else:
                # action is "approve" from Review page
                clinical_indication_panel.pending = False
                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip_id,
                    note=History.clinical_indication_panel_approved(cip_id),
                    user=request.user,
                )

            clinical_indication_panel.save()

        return redirect("review")


def clinical_indication_superpanel(
    request: HttpRequest, cisp_id: str
) -> HttpResponse:
    """
    Clinical indication panel page

    Shows all clinical indication panel links
    """

    if request.method == "GET":
        clinical_indication_superpanel = (
            ClinicalIndicationSuperPanel.objects.filter(id=cisp_id)
            .values(
                "clinical_indication_id__r_code",
                "clinical_indication_id__name",
                "superpanel_id__panel_name",
                "superpanel_id__panel_version",
                "superpanel_id",
                "clinical_indication_id",
                "current",
                "pending",
                "id",
            )
            .first()
        )

        releases = CiSuperpanelTdRelease.objects.filter(
            ci_superpanel=clinical_indication_superpanel["id"]
        ).values(
            "td_release_id__release",
            "td_release_id__td_source",
            "td_release_id__config_source",
            "td_release_id__td_date",
            "id",
        )

        return render(
            request,
            "web/info/clinical_indication_superpanel.html",
            {"cisp": clinical_indication_superpanel, "releases": releases},
        )

    elif request.method == "POST":
        action = request.POST.get("action")
        clinical_indication_superpanel = (
            ClinicalIndicationSuperPanel.objects.get(id=cisp_id)
        )

        with transaction.atomic():
            if action == "revert":
                # action is "revert" from Review page
                ClinicalIndicationSuperPanelHistory.objects.create(
                    clinical_indication_superpanel_id=cisp_id,
                    note=History.clinical_indication_superpanel_reverted(
                        id=cisp_id,
                        metadata="current",
                        old_value=clinical_indication_superpanel.current,
                        new_value=not clinical_indication_superpanel.current,
                        review=True,
                    ),
                    user=request.user,
                )

                clinical_indication_superpanel.current = (
                    not clinical_indication_superpanel.current
                )
                clinical_indication_superpanel.pending = False
            if action == "approve":
                # action is "approve" from Review page
                clinical_indication_superpanel.pending = False
                ClinicalIndicationSuperPanelHistory.objects.create(
                    clinical_indication_superpanel_id=cisp_id,
                    note=History.clinical_indication_superpanel_approved(
                        cisp_id
                    ),
                    user=request.user,
                )

            clinical_indication_superpanel.save()

        return redirect("review")


@permission_required("staff", raise_exception=False)
def review(request: HttpRequest) -> HttpResponse:
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
    action_pg = None

    approve_bool = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve_pg":
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
                    user=request.user,
                )

                PanelGeneHistory.objects.create(
                    panel_gene_id=panel_gene_id,
                    note=History.panel_gene_metadata_changed(
                        "active",
                        not panel_gene.active,
                        panel_gene.active,
                    ),
                    user=request.user,
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
                panel_gene: PanelGene = PanelGene.objects.get(id=panel_gene_id)

                PanelGeneHistory.objects.create(
                    panel_gene_id=panel_gene_id,
                    note=History.panel_gene_reverted("manual review"),
                    user=request.user,
                )

                PanelGeneHistory.objects.create(
                    panel_gene_id=panel_gene_id,
                    note=History.panel_gene_metadata_changed(
                        "active",
                        panel_gene.active,
                        not panel_gene.active,
                    ),
                    user=request.user,
                )

                panel_gene.active = not panel_gene.active
                panel_gene.pending = False
                panel_gene.save()

        return redirect("panel", panel_id=panel_gene.panel_id)

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
            indication.reason = (
                indication_history.note if indication_history else "NEW"
            )

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
            cip["panel_id__panel_version"] = "None"

    # clinical indication - superpanel
    clinical_indication_superpanels: QuerySet[ClinicalIndicationPanel] = (
        ClinicalIndicationSuperPanel.objects.filter(pending=True)
        .values(
            "clinical_indication_id",
            "clinical_indication_id__name",
            "clinical_indication_id__r_code",
            "superpanel_id",
            "superpanel_id__panel_name",
            "superpanel_id__panel_version",
            "current",
            "id",
        )
        .order_by("clinical_indication_id__r_code")
    )

    # normalize panel version
    for cisp in clinical_indication_superpanels:
        if cisp["superpanel_id__panel_version"]:
            cisp["superpanel_id__panel_version"] = normalize_version(
                cisp["superpanel_id__panel_version"]
            )
        else:
            cisp["superpanel_id__panel_version"] = "None"

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
            "cisps": clinical_indication_superpanels,
            "panel_gene": panel_gene,
            "action_pg": action_pg,
            "approve_bool": approve_bool,
        },
    )


def gene(request: HttpRequest, gene_id: int) -> HttpResponse:
    """
    Page to view individual gene information
    - shows all the Panel associated with the gene


    Args:
        gene_id (int): gene id
    """
    try:
        gene = Gene.objects.get(id=gene_id)
    except Gene.DoesNotExist:
        return render(request, "web/info/gene.html")

    associated_panels = PanelGene.objects.filter(gene_id=gene_id).values(
        "panel_id__panel_name",
        "panel_id",
        "active",
    )

    transcripts = TranscriptReleaseTranscript.objects.filter(
        transcript_id__gene_id=gene_id
    ).values(
        "transcript_id__transcript",
        "release_id__source_id__source",
        "release_id__reference_genome_id__name",
        "default_clinical",
        "release_id__release",
    )

    return render(
        request,
        "web/info/gene.html",
        {
            "gene": gene,
            "panels": associated_panels,
            "transcripts": transcripts,
        },
    )


def _parse_excluded_hgncs_from_bytes(file: TemporaryUploadedFile) -> set[str]:
    """
    Function to parse a file containing hgnc ids that are excluded from the genepanel creation
    This function is similar to "parse_excluded_hgncs_from_file" from
    panels_backend/management/commands/utils.py but takes different type of input

    :param: file: TemporaryUploadedFile - this is an uploaded file from the front-end in bytes

    :return: set[str] - a set of hgnc ids that are excluded
    """
    try:
        df = pd.read_csv(BytesIO(file.read()), delimiter="\t", dtype=str)

        df = df[
            df["Locus type"].str.contains("rna", case=False)
            | df["Approved name"].str.contains(
                "mitochondrially encoded", case=False
            )
        ]
    except Exception as e:
        print("Error parsing file: ", e)
        return set()

    return set(df["HGNC ID"].tolist())


@permission_required("staff", raise_exception=False)
def _add_panel_genes_to_genepanel(
    panel_id: str,
    panel_id_to_genes: dict[str, list[WebGene]],
    genepanel: WebGenePanel,
) -> None:
    """
    Small helper function to add panel genes to genepanel object
    used in genepanel function

    :param: panel_id: str - panel id
    :param: panel_id_to_genes: dict[str, list[WebGene]] - dict of panel id to list of WebGene
    :param: genepanel: GenePanel - genepanel object

    :return: None
    """
    for gene in PanelGene.objects.filter(panel_id=panel_id).values(
        "gene_id__hgnc_id", "gene_id", "panel_id"
    ):
        gene_id = gene["gene_id"]
        hgnc_id = gene["gene_id__hgnc_id"]

        panel_id_to_genes[panel_id].append(WebGene(gene_id, hgnc_id))

        print(panel_id_to_genes[panel_id])

        genepanel.hgncs.append(WebGene(gene_id, hgnc_id))


@permission_required("staff", raise_exception=False)
def genepanel(
    request: HttpRequest,
) -> HttpResponse:
    """
    Genepanel page where user view R code, clinical indication name
    its associated panels and genes.
    """

    success = None
    warnings = []

    pending_clinical_indication_panels = (
        ClinicalIndicationPanel.objects.filter(pending=True).exists()
    )
    pending_clinical_indication_superpanels = (
        ClinicalIndicationSuperPanel.objects.filter(pending=True).exists()
    )
    pending_panel_genes = PanelGene.objects.filter(pending=True).exists()
    from django.db.models import Count, Q

    # check if there're clinical indication with more than one active links
    clinical_indication_with_more_than_one_active_links = (
        ClinicalIndicationPanel.objects.values("clinical_indication_id")
        .annotate(panel_count=Count("panel_id"))
        .filter(panel_count__gt=1)
        .annotate(true_current_count=Count("id", filter=Q(current=True)))
        .filter(true_current_count__gt=1)
    )

    # if there's no CiPanelAssociation date column, return empty list
    if not ClinicalIndicationPanel.objects.filter(
        current=True, pending=False
    ).exists():
        return render(request, "web/info/genepanel.html")

    # if there're pending CiPanel / CiSuperPanel / PanelGene
    # display notice in front end
    if pending_clinical_indication_panels:
        warnings.append("Pending Clinical Indication Panel(s) found.")
    if pending_clinical_indication_superpanels:
        warnings.append("Pending Clinical Indication Super Panel(s) found.")
    if pending_panel_genes:
        warnings.append("Pending Panel Gene(s) found.")
    if clinical_indication_with_more_than_one_active_links:
        warnings.append(
            "Clinical Indication(s) with more than one active links found."
        )

    genepanels: list[WebGenePanel] = []
    panel_id_to_genes: dict[str, list[WebGene]] = collections.defaultdict(list)

    for row in ClinicalIndicationPanel.objects.filter(
        current=True, pending=False
    ).values(
        "clinical_indication_id__r_code",
        "clinical_indication_id__name",
        "panel_id",
        "clinical_indication_id",
        "panel_id__panel_name",
        "panel_id__panel_version",
    ):
        panel_id = row["panel_id"]

        genepanel = WebGenePanel(
            row["clinical_indication_id__r_code"],
            row["clinical_indication_id__name"],
            row["clinical_indication_id"],
            row["panel_id"],
            row["panel_id__panel_name"],
            normalize_version(row["panel_id__panel_version"])
            if row["panel_id__panel_version"]
            else None,
            [],
        )
        _add_panel_genes_to_genepanel(panel_id, panel_id_to_genes, genepanel)

        genepanels.append(genepanel)

    # deal with CiSuperPanel
    for row in ClinicalIndicationSuperPanel.objects.filter(
        current=True, pending=False
    ).values(
        "clinical_indication_id__r_code",
        "clinical_indication_id__name",
        "clinical_indication_id",
        "superpanel_id",
        "superpanel_id__panel_name",
        "superpanel_id__panel_version",
    ):
        superpanel_id = row["superpanel_id"]

        genepanel = WebGenePanel(
            row["clinical_indication_id__r_code"],
            row["clinical_indication_id__name"],
            row["clinical_indication_id"],
            row["superpanel_id"],
            row["superpanel_id__panel_name"],
            normalize_version(row["superpanel_id__panel_version"])
            if row["superpanel_id__panel_version"]
            else None,
            [],
            True,
            [],  # child panels
        )

        for child_panel in PanelSuperPanel.objects.filter(
            superpanel_id=superpanel_id
        ).values(
            "panel_id__panel_name",
            "panel_id",
            "panel_id__panel_version",
        ):
            child_panel_id = child_panel["panel_id"]

            genepanel.child_panels.append(
                WebChildPanel(
                    child_panel["panel_id"],
                    child_panel["panel_id__panel_name"],
                    normalize_version(child_panel["panel_id__panel_version"])
                    if child_panel["panel_id__panel_version"]
                    else None,
                )
            )

            if child_panel_id in panel_id_to_genes:
                genepanel.hgncs.extend(panel_id_to_genes[child_panel_id])
                continue

            _add_panel_genes_to_genepanel(
                child_panel_id, panel_id_to_genes, genepanel
            )

        genepanels.append(genepanel)

    if request.method == "POST":
        # return errors if there're pending links in Manual Review
        if (
            pending_clinical_indication_panels
            or pending_clinical_indication_panels
            or pending_clinical_indication_panels
        ):
            return render(
                request,
                "web/info/genepanel.html",
                {
                    "genepanels": genepanels,
                    "warnings": warnings,
                    "error": "Please resolve all pending links before uploading to DNAnexus.",
                },
            )

        project_id = request.POST.get("project_id").strip()
        dnanexus_token = request.POST.get("dnanexus_token").strip()
        hgnc = request.FILES.get("hgnc_upload")

        # validate hgnc columns
        if missing_columns := check_missing_columns(
            pd.read_csv(BytesIO(hgnc.read()), delimiter="\t"),
            ["HGNC ID", "Locus type", "Approved name"],
        ):
            return render(
                request,
                "web/info/genepanel.html",
                {
                    "genepanels": genepanels,
                    "error": "Missing columns: "
                    + ", ".join(missing_columns)
                    + " in HGNC file.",
                },
            )

        rnas = _parse_excluded_hgncs_from_bytes(hgnc)

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

            if project_name.startswith("001") or project_name.startswith(
                "002"
            ):
                return render(
                    request,
                    "web/info/genepanel.html",
                    {
                        "genepanels": genepanels,
                        "error": "Uploading to 001 or 002 project is not allowed.",
                    },
                )

            # generate result and sort
            file_result = []
            for gp in genepanels:
                if gp.superpanel:
                    for child_panel in gp.child_panels:
                        for gene in panel_id_to_genes[child_panel.id]:
                            if (
                                gene.hgnc in HGNC_IDS_TO_OMIT
                                or gene.hgnc in rnas
                            ):
                                continue

                            file_result.append(
                                [
                                    f"{gp.r_code}_{gp.ci_name}",
                                    f"{gp.panel_name}_{gp.panel_version}",
                                    gene.hgnc,
                                ]
                            )
                else:
                    for gene in gp.hgncs:
                        if gene.hgnc in HGNC_IDS_TO_OMIT or gene.hgnc in rnas:
                            continue

                        file_result.append(
                            [
                                f"{gp.r_code}_{gp.ci_name}",
                                f"{gp.panel_name}_{gp.panel_version}",
                                gene.hgnc,
                            ]
                        )

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
                {"genepanels": genepanels, "error": e},
            )

        success = True

    return render(
        request,
        "web/info/genepanel.html",
        {"genepanels": genepanels, "warnings": warnings, "success": success},
    )


@permission_required("staff", raise_exception=False)
def add_gene(request: HttpRequest) -> HttpResponse:
    """
    url name "gene_add"

    Handle gene addition page (GET) and form submission (POST)
    """

    if request.method == "GET":
        return render(request, "web/addition/add_gene.html")
    else:
        # parse submitted form
        form = GeneForm(request.POST)

        if form.is_valid():
            hgnc_id: str = request.POST.get("hgnc_id").strip()
            gene_symbol: str = request.POST.get("gene_symbol").strip()

            # if form valid, create gene
            gene = Gene.objects.create(
                hgnc_id=hgnc_id.upper(),
                gene_symbol=gene_symbol.upper(),
            )

            return redirect("gene", gene_id=gene.id)

        else:
            return render(
                request,
                "web/addition/add_gene.html",
                {
                    "errors": form.errors if not form.is_valid() else None,
                },
            )


def ajax_genes(request: HttpRequest) -> JsonResponse:
    """
    Ajax fetch call to get all genes
    """
    if request.method == "GET":
        genes = list(Gene.objects.all().order_by("hgnc_id").values())

        return JsonResponse({"data": genes}, safe=False)


def _giving_transcript_clinical_context(
    transcripts: list[dict[str, str]], release_ids: list[str]
) -> list[dict[str, str | bool | None]]:
    """
    Function to give transcripts clinical context by querying TranscriptReleaseTranscript

    Args:
        transcripts: list of transcripts in dict form
        release_ids: list of release ids

    Returns:
        list of transcripts with clinical context in the form of
        dict with keys:
            - hgnc_id
            - gene_id
            - transcript
            - clinical
            - source
            - source_id

    """

    relevant_transcripts = TranscriptReleaseTranscript.objects.filter(
        transcript_id__in=set([tx["id"] for tx in transcripts]),
        release_id__in=release_ids,
        default_clinical=True,
    ).values(
        "transcript__transcript",
        "transcript_id",
        "release_id__release",
        "release_id__source_id__source",
        "release_id__source_id",
    )

    clinical_transcripts_to_source: dict[str, str] = {
        str(c["transcript_id"])
        + c["transcript__transcript"]: c["release_id__source_id__source"]
        for c in relevant_transcripts
    }

    source_to_source_id = {
        c["release_id__source_id__source"]: c["release_id__source_id"]
        for c in relevant_transcripts
    }

    return [
        {
            "hgnc_id": tx["gene_id__hgnc_id"],
            "gene_id": tx["gene_id"],
            "transcript": tx["transcript"],
            "clinical": (str(tx["id"]) + tx["transcript"])
            in clinical_transcripts_to_source,
            "source": clinical_transcripts_to_source.get(
                (str(tx["id"]) + tx["transcript"]), None
            ),
            "source_id": source_to_source_id.get(
                clinical_transcripts_to_source.get(
                    (str(tx["id"]) + tx["transcript"]), None
                ),
                None,
            ),
        }
        for tx in transcripts
    ]


def ajax_gene_transcripts(
    request: HttpRequest, reference_genome: str
) -> JsonResponse:
    """
    Ajax fetch call to get all transcripts for a given reference genome.
    Returns a json response as this will be requested by the datatable in the front-end

    The content of the json response is a list of transcripts with clinical context
    See function: `_giving_transcript_clinical_context`
    """
    refgenome = ReferenceGenome.objects.filter(name=reference_genome).first()

    latest_select = get_latest_transcript_release("MANE Select", refgenome)
    latest_plus_clinical = get_latest_transcript_release(
        "MANE Plus Clinical", refgenome
    )
    latest_hgmd = get_latest_transcript_release("HGMD", refgenome)

    # lack of latest release version in the backend
    if None in [latest_select, latest_plus_clinical, latest_hgmd]:
        return JsonResponse(
            {
                "data": [
                    {
                        "hgnc_id": None,
                        "transcript": None,
                        "clinical": None,
                        "source": None,
                    }
                ]
            },
            safe=False,
        )

    transcripts = (
        Transcript.objects.order_by("gene_id")
        .filter(reference_genome=refgenome)
        .values("gene_id__hgnc_id", "gene_id", "transcript", "id")
    )

    return JsonResponse(
        {
            "data": _giving_transcript_clinical_context(
                transcripts,
                [latest_hgmd.id, latest_select.id, latest_plus_clinical.id],
            )
        },
        safe=False,
    )


def genetranscriptsview(request: HttpRequest) -> HttpResponse:
    """
    Page where it display gene and their transcripts (clinical and non-clinical)

    NOTE: this page only display the transcript from the latest TranscriptRelease
    as in it will only display the gene and transcripts that are suppose to make it
    into the g2t output file.

    For transcript of different TranscriptRelease, this should be viewed under individual
    gene page which is more detailed
    """
    return render(request, "web/info/genetranscriptsview.html")


@permission_required("staff", raise_exception=False)
def genetranscripts(request: HttpRequest) -> HttpResponse:
    """
    Page where it display gene and their transcripts (clinical and non-clinical)
    This page also contain form to generate g2t file and upload to dnanexus

    NOTE: this page only display the transcript from the latest TranscriptRelease
    as in it will only display the gene and transcripts that are suppose to make it
    into the g2t output file.

    For transcript of different TranscriptRelease, this should be viewed under individual
    gene page which is more detailed
    """

    if request.method == "POST":
        project_id = request.POST.get("project_id").strip()
        dnanexus_token = request.POST.get("dnanexus_token").strip()
        reference_genome = request.POST.get("reference_genome").strip()

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

            if project_name.startswith("001") or project_name.startswith(
                "002"
            ):
                return render(
                    request,
                    "web/info/genetranscripts.html",
                    {
                        "error": "Uploading to 001 or 002 project is not allowed."
                    },
                )

            current_datetime = dt.datetime.today().strftime("%Y%m%d")

            transcripts = ajax_gene_transcripts(
                HttpRequest, reference_genome=reference_genome
            )

            # write result to dnanexus file
            with dx.new_dxfile(
                name=f"{current_datetime}_g2t.tsv",
                project=project_id,
                media_type="text/plain",
            ) as f:
                for row in json.loads(transcripts.content)["data"]:
                    hgnc_id = row["hgnc_id"]
                    transcript = row["transcript"]
                    source = row.get("source")

                    data = "\t".join(
                        [hgnc_id, transcript, "True" if source else "False"]
                    )
                    f.write(f"{data}\n")

            return render(
                request, "web/info/genetranscripts.html", {"success": True}
            )

        except Exception as e:
            return render(
                request, "web/info/genetranscripts.html", {"error": e}
            )

    return render(request, "web/info/genetranscripts.html")


def transcript_source(request: HttpRequest, ts_id: int) -> HttpResponse:
    """
    Page to view transcript source information and its releases

    Args:
        ts_id (int): transcript source id

    Returns:
        HttpResponse to render transcript source page

    """
    tx_source = TranscriptSource.objects.get(id=ts_id)

    tx_releases = (
        TranscriptRelease.objects.filter(source=ts_id)
        .values(
            "id",
            "release",
            "created",
            "reference_genome__name",
        )
        .order_by("-created")
    )

    for release in tx_releases:
        release["files"] = TranscriptReleaseTranscriptFile.objects.filter(
            transcript_release=release["id"]
        ).values("transcript_file__file_type", "transcript_file__file_id")

    return render(
        request,
        "web/info/transcript_source.html",
        {"tx_releases": tx_releases, "tx_source": tx_source},
    )


@permission_required("staff", raise_exception=False)
def seed(request: HttpRequest) -> HttpResponse:
    """
    Handle seed page:
    Currently only handle Test Directory seed

    TODO: Handle other seed (transcript)
    """

    error = None

    if request.method == "POST":
        try:
            # if force update (True), disregard td version and continue seeding Test Directory
            force_update = request.POST.get("force")
            td_version = request.POST.get("version")

            test_directory_data = json.loads(
                request.FILES.get("td_upload").read().decode()
            )

            insert_test_directory_data(
                test_directory_data,
                td_version,
                True if force_update else False,
                request.user,
            )

            error = False
        except Exception as e:
            error = e

    return render(request, "web/info/seed.html", {"error": error})
