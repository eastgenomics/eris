from django.urls import path

from . import views

urlpatterns = [
    # index
    path("", views.index, name="index"),
    # info
    path("panel/<int:panel_id>/", views.panel, name="panel"),
    path("ci/<int:ci_id>/", views.clinical_indication, name="clinical_indication"),
    path(
        "clinical_indication_panels",
        views.clinical_indication_panels,
        name="clinical_indication_panels",
    ),
    path("gene/<int:gene_id>/", views.gene, name="gene"),
    path("genepanel/", views.genepanel, name="genepanel"),
    path("genes/", views.genes, name="genes"),
    # addition
    path("ci/add/", views.add_clinical_indication, name="ci_add"),
    path("panel/add", views.add_panel, name="panel_add"),
    path("ci_panel/add/<int:ci_id>", views.add_ci_panel, name="ci_panel_add"),
    # edit
    path("panel/<int:panel_id>/gene/edit/", views.edit_gene, name="gene_edit"),
    # history
    path("history/", views.history, name="history"),
    # deactivate clinical indication panel
    path(
        "clinical_indication_panel/<int:cip_id>/deactivate",
        views.activate_or_deactivate_clinical_indication_panel,
        name="activate_or_deactivate_clinical_indication_panel",
    ),
    # review
    path("review/", views.review, name="review"),
]
