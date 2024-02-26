from django.urls import include, path

from . import views

urlpatterns = [
    # index
    path("", views.index, name="index"),
    # login and related
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/login/", views.login, name="login"),
    path("accounts/logout/", views.logout, name="logout"),
    # info
    path("panel/<int:panel_id>/", views.panel, name="panel"),
    path("superpanel/<int:superpanel_id>/", views.superpanel, name="superpanel"),
    path(
        "ci/<int:ci_id>/",
        views.clinical_indication,
        name="clinical_indication",
    ),
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
    path("ts/<int:ts_id>/", views.transcript_source, name="transcript_source"),
    # seed test directory
    path("seed", views.seed, name="seed"),
    path("genepanel/", views.genepanel, name="genepanel"),
    path(
        "genetranscriptsview/",
        views.genetranscriptsview,
        name="genetranscriptsview",
    ),
    path(
        "genetranscripts/",
        views.genetranscripts,
        name="genetranscripts",
    ),
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
    path(
        "api/genetranscripts/<str:reference_genome>/",
        views.ajax_gene_transcripts,
        name="api_genetranscripts",
    ),
]
