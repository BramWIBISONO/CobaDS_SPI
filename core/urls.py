from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("cabang-aktif/", views.switch_branch, name="switch_branch"),
    path("notifikasi/", views.notifikasi_list, name="notifikasi"),
    path("notifikasi/<int:pk>/baca/", views.notifikasi_baca, name="notifikasi_baca"),
    path("notifikasi/baca-semua/", views.notifikasi_baca_semua, name="notifikasi_baca_semua"),
]
