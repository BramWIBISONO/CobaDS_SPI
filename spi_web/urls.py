from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("", include("dashboards.urls")),
    path("", include("students.urls")),
    path("", include("classes.urls")),
    path("", include("masterdata.urls")),
    path("akun/", include("accounts.urls")),
    path("impor/", include("importer.urls")),
    path("cabang/", include("branches.urls")),
    path("manajemen/", include("management.urls")),
    path("akademik/", include("akademik.urls")),
]
