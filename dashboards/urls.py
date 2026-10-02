from django.urls import path

from . import views

app_name = "dashboards"
urlpatterns = [
    path("cari-murid/", views.cari, name="cari"),
]
