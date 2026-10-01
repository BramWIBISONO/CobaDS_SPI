from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("cabang-aktif/", views.switch_branch, name="switch_branch"),
]
