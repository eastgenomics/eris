import secrets
import string
import collections
import json
from itertools import chain
import dxpy as dx
import datetime as dt
from packaging.version import Version

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import QuerySet, Q, F
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
    ClinicalIndicationSuperPanel,
    CiPanelTdRelease,
    CiSuperpanelTdRelease,
    ClinicalIndicationTestMethodHistory,
    PanelGene,
    PanelGeneHistory,
    Transcript,
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
)


def index(request):
    """
    Main page. Display all clinical indications and panels
    """

    # fetch all clinical indications
    clinical_indications: list[
        ClinicalIndication
    ] = ClinicalIndication.objects.order_by("r_code").all()

    # fetch all panels
    panels: list[dict] = Panel.objects.order_by("panel_name").all()

    # normalize panel version
    for panel in panels:
        panel.panel_version = normalize_version(panel.panel_version)
        panel.superpanel = False

    super_panels = SuperPanel.objects.all()

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
    for row in clinical_indication_panels:
        superpanel_id = row["id"]

        releases = CiSuperpanelTdRelease.objects.filter(
            ci_superpanel_id=superpanel_id
        ).values(
            "td_release_id__release",
        )

        row["td_release"] = (
            max([Version(release["td_release_id__release"]) for release in releases])
            if releases
            else None
        )

        row["superpanel"] = False

    for row in clinical_indication_sp:
        id = row["id"]

        releases = CiPanelTdRelease.objects.filter(ci_panel_id=id).values(
            "td_release_id__release",
        )

        row["td_release"] = (
            max([Version(release["td_release_id__release"]) for release in releases])
            if releases
            else None
        )

        row["superpanel"] = True

    all_clinical_indication_p_and_sp = list(
        chain(clinical_indication_panels, clinical_indication_sp)
    )

    # fetch Test Directory Releases
    td_releases = TestDirectoryRelease.objects.all()

    return render(
        request,
        "web/index.html",
        {
            "cis": clinical_indications,
            "panels": all_panels,
            "cips": all_clinical_indication_p_and_sp,
            "td_releases": td_releases,
        },
    )


def panel(request, panel_id: int):
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
            normalize_version(panel.panel_version) if panel.panel_version else None
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


def superpanel(request, superpanel_id: int):
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

    child_panels = PanelSuperPanel.objects.filter(superpanel_id=superpanel.id).values(
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


def clinical_indication(request, ci_id: int):
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
            {"ci": ci, "ci_panels": ci_panels, "tm_history": test_method_history},
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
                    indication_history.note.split("to")[0].split("from")[-1].strip()
                )

                ClinicalIndicationTestMethodHistory.objects.create(
                    clinical_indication_id=ci_id,
                    user="online",
                    note=History.clinical_indication_metadata_changed(
                        "test_method",
                        ci.test_method,
                        previous_test_method,
                    ),
                )

                ci.pending = False
                ci.test_method = previous_test_method
                ci.save()

            return redirect("review")


def add_clinical_indication(request):
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
                clinical_indication = ClinicalIndication.objects.get(r_code=r_code)
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


def add_panel(request):
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
            # if valid, create Panel
            panel: Panel = Panel.objects.create(
                external_id=form.cleaned_data.get("external_id"),
                panel_name=form.cleaned_data.get("panel_name"),
                panel_version=form.cleaned_data.get("panel_version"),
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


def add_ci_panel(request):
    """
    Add clinical indication panel page
    """
    if request.method == "GET":
        clinical_indications = ClinicalIndication.objects.all().order_by("r_code")

        panels = (
            Panel.objects.filter(pending=False)
            .all()
            .order_by("external_id", "panel_name")
        )

        for panel in panels:
            panel.panel_version = (
                normalize_version(panel.panel_version) if panel.panel_version else ""
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
            cip_instance, created = ClinicalIndicationPanel.objects.get_or_create(
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
                clinical_indication_panel=cip_instance.id,
                note=History.clinical_indication_panel_created(),
            )

        return redirect(
            "clinical_indication_panel",
            cip_id=cip_instance.id,
        )


def _get_clinical_indication_panel_history():
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


def clinical_indication_panel(request, cip_id: str):
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
    else:
        action = request.POST.get("action")
        clinical_indication_panel = ClinicalIndicationPanel.objects.get(id=cip_id)

        if action in ["activate", "deactivate"]:
            if action == "activate":
                clinical_indication_panel.current = True
                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip_id,
                    note=History.clinical_indication_panel_activated(cip_id, True),
                )
            elif action == "deactivate":
                clinical_indication_panel.current = False
                ClinicalIndicationPanelHistory.objects.create(
                    clinical_indication_panel_id=cip_id,
                    note=History.clinical_indication_panel_deactivated(cip_id, True),
                )
            clinical_indication_panel.pending = True  # require manual review
        elif action == "revert":
            # action is "revert" from Review page
            clinical_indication_panel.current = not clinical_indication_panel.current
            clinical_indication_panel.pending = False

            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel_id=cip_id,
                note=History.clinical_indication_panel_reverted(
                    id=cip_id,
                    old_value=clinical_indication_panel.current,
                    new_value=not clinical_indication_panel.current,
                    review=True,
                ),
            )
        else:
            # action is "approve" from Review page
            clinical_indication_panel.pending = False
            ClinicalIndicationPanelHistory.objects.create(
                clinical_indication_panel_id=cip_id,
                note=History.clinical_indication_panel_approved(cip_id),
            )

        clinical_indication_panel.save()

        return redirect("review")


def clinical_indication_superpanel(request, cisp_id: str):
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
            indication.reason = indication_history if indication_history else "NEW"

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
            "action_pg": action_pg,
            "approve_bool": approve_bool,
        },
    )


def gene(request, gene_id: int) -> None:
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
        "release_id__reference_genome_id__reference_genome",
        "default_clinical",
    )

    return render(
        request,
        "web/info/gene.html",
        {"gene": gene, "panels": associated_panels, "transcripts": transcripts},
    )


def genepanel(
    request,
):  # TODO: revisit once output PR is merged because there's some function change in that PR
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


def add_gene(request):
    """
    url name "gene_add"
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

    return render(
        request,
        "web/addition/add_gene.html",
        {"genes": genes},
    )


def ajax_genes(request):
    """
    Ajax fetch call to get all genes
    """
    if request.method == "GET":
        genes = list(Gene.objects.all().order_by("hgnc_id").values())

        return JsonResponse({"data": genes}, safe=False)


def ajax_gene_transcripts(request, reference_genome: str):
    if request.method == "GET":
        # TODO: revisit once tx is sorted

        # fetch latest transcript
        transcripts = TranscriptReleaseTranscript.objects.values(
            "transcript_id__gene_id__hgnc_id",
            "transcript_id__gene_id",
            "transcript_id__transcript",
            "release_id__source_id__source",
            "default_clinical",
        )

        # convert to list of [hgnc-id, transcript, sources, which one is clinical]
        hgnc_to_gene_id = {}
        hgnc_to_txs = collections.defaultdict(list)
        hgnc_tx_to_assessed_sources = collections.defaultdict(list)
        hgnc_tx_to_clinical_source = collections.defaultdict(list)

        for tx in transcripts:
            hgnc = tx["transcript_id__gene_id__hgnc_id"]
            transcript = tx["transcript_id__transcript"]

            if hgnc not in hgnc_to_gene_id:
                hgnc_to_gene_id[hgnc] = tx["transcript_id__gene_id"]

            if transcript not in hgnc_to_txs[hgnc]:
                hgnc_to_txs[hgnc].append(transcript)

            if tx["default_clinical"]:
                hgnc_tx_to_clinical_source[hgnc + transcript].append(
                    tx["release_id__source_id__source"]
                )

            hgnc_tx_to_assessed_sources[hgnc + transcript].append(
                tx["release_id__source_id__source"]
            )

        trancript_list = []

        for hgnc, txs in hgnc_to_txs.items():
            for tx in txs:
                trancript_list.append(
                    {
                        "gene_id": hgnc_to_gene_id[hgnc],
                        "hgnc_id": hgnc,
                        "tx": tx,
                        "sources": ", ".join(
                            hgnc_tx_to_assessed_sources.get(hgnc + tx, [])
                        ),
                        "clinical_sources": hgnc_tx_to_clinical_source.get(
                            hgnc + tx, []
                        ),
                    }
                )


def genetotranscript(request):
    """
    g2t page where it display gene and their transcripts (clinical and non-clinical)

    NOTE: this page only display the transcript from the latest TranscriptRelease
    as in it will only display the gene and transcripts that are suppose to make it
    into the g2t output file.

    For transcript of different TranscriptRelease, this should be viewed under individual
    gene page which is more detailed
    """

    return render(request, "web/info/gene2transcript.html")

    # if request.method == "POST":  # TODO: revisit once tx is sorted
    #     project_id = request.POST.get("project_id").strip()
    #     dnanexus_token = request.POST.get("dnanexus_token").strip()

    #     try:
    #         # login dnanexus
    #         dx.set_security_context(
    #             {
    #                 "auth_token_type": "Bearer",
    #                 "auth_token": dnanexus_token,
    #             }
    #         )

    #         # check dnanexus login
    #         dx.api.system_whoami()

    #         # check dnanexus project id
    #         dx.DXProject(project_id)

    #         project_metadata: dict = dx.DXProject(project_id).describe()
    #         project_name: str = project_metadata.get("name", "")

    #         if project_name.startswith("001") or project_name.startswith("002"):
    #             return render(
    #                 request,
    #                 "web/info/gene2transcript.html",
    #                 {
    #                     "transcripts": transcripts,
    #                     "error": "Uploading to 001 or 002 project is not allowed.",
    #                 },
    #             )

    #         current_datetime = dt.datetime.today().strftime("%Y%m%d")

    #         # write result to dnanexus file
    #         with dx.new_dxfile(
    #             name=f"{current_datetime}_g2t.tsv",
    #             project=project_id,
    #             media_type="text/plain",
    #         ) as f:
    #             for row in transcripts:
    #                 hgnc_id = row["gene_id__hgnc_id"]
    #                 transcript = row["transcript"]
    #                 source = row.get("source")

    #                 data = "\t".join(
    #                     [hgnc_id, transcript, "clinical" if source else "non-clinical"]
    #                 )
    #                 data = "\t".join(
    #                     [hgnc_id, transcript, "clinical" if source else "non-clinical"]
    #                 )
    #                 f.write(f"{data}\n")

    #     except Exception as e:
    #         return render(
    #             request,
    #             "web/info/gene2transcript.html",
    #             {"transcripts": transcripts, "error": e},
    #         )

    #     success = True


def seed(request):
    """
    This page allows file upload (test directory json file)
    and will insert the data into the database
    """

    error = None

    if request.method == "POST":
        try:
            force_update = request.POST.get("force")
            td_version = request.POST.get("version")

            test_directory_data = json.loads(
                request.FILES.get("td_upload").read().decode()
            )

            insert_test_directory_data(
                test_directory_data,
                td_version,
                True if force_update else False,
            )

            error = False
        except Exception as e:
            error = e

    return render(request, "web/info/seed.html", {"error": error})


def panel_gene(request, panel_gene_id: int):
    pass
