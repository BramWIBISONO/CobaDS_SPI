from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("", include("dashboards.urls")),
    path("akun/", include("accounts.urls")),
    path("impor/", include("importer.urls")),
    path("cabang/", include("branches.urls")),
]
