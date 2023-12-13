from django.urls import path

from . import views

urlpatterns = [
    # index
    path("", views.index, name="index"),
    # info
    path("panel/<int:panel_id>/", views.panel, name="panel"),
    path("superpanel/<int:superpanel_id>/", views.superpanel, name="superpanel"),
    path("ci/<int:ci_id>/", views.clinical_indication, name="clinical_indication"),
    path("gene/<int:gene_id>/", views.gene, name="gene"),
    path(
        "cip/<int:cip_id>/",
        views.clinical_indication_panel,
        name="clinical_indication_panel",
    ),
    path(
        "cisp/<int:cisp_id>/",
        views.clinical_indication_superpanel,
        name="clinical_indication_superpanel",
    ),
    # seed test directory
    path("seed", views.seed, name="seed"),
    path("genepanel/", views.genepanel, name="genepanel"),
    path("g2t/", views.genetotranscript, name="g2t"),
    # addition
    path("ci/add/", views.add_clinical_indication, name="ci_add"),
    path("panel/add", views.add_panel, name="panel_add"),
    path("ci_panel/add", views.add_ci_panel, name="cip_add"),
    path("gene/add", views.add_gene, name="gene_add"),
    # history
    path("history/", views.history, name="history"),
    # review
    path("review/", views.review, name="review"),
    # api
    path("api/genes/", views.ajax_genes, name="api_genes"),
]
