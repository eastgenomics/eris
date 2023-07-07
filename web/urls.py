from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("panel/<int:panel_id>/", views.panel, name="panel"),
    path("ci/<int:ci_id>/", views.ci, name="clinical_indication"),
]
