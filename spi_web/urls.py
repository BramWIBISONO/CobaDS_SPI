from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("akun/", include("accounts.urls")),
    path("impor/", include("importer.urls")),
]
