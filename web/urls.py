from django.urls import path

from . import views

urlpatterns = [
    # index
    path("", views.index, name="index"),
    # info
    path("panel/<int:panel_id>/", views.panel, name="panel"),
    path("ci/<int:ci_id>/", views.clinical_indication, name="clinical_indication"),
    # addition
    path("ci/add/", views.add_clinical_indication, name="ci_add"),
    path("panel/add", views.add_panel, name="panel_add"),
    path("ci_panel/add/<int:ci_id>", views.add_ci_panel, name="ci_panel_add"),
]
