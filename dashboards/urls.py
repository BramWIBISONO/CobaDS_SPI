from django.urls import path

from . import views

app_name = "dashboards"
urlpatterns = [
    path("laporan/", views.laporan, name="laporan"),
    path("cari-murid/", views.cari, name="cari"),
]
