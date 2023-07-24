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
    # addition
    path("ci/add/", views.add_clinical_indication, name="ci_add"),
    path("panel/add", views.add_panel, name="panel_add"),
    path("ci_panel/add/<int:ci_id>", views.add_ci_panel, name="ci_panel_add"),
    path("panel/<int:panel_id>/gene/add/", views.add_gene, name="gene_add"),
    # history
    path("history/", views.history, name="history"),
]
