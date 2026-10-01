from django.urls import path

from . import views

app_name = "importer"
urlpatterns = [
    path("", views.upload, name="upload"),
    path("<int:pk>/", views.preview, name="preview"),
    path("<int:pk>/simpan/", views.commit, name="commit"),
]
