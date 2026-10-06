from django.urls import path

from . import views, views_mgmt as v

app_name = "management"
urlpatterns = [
    path("", views.center, name="center"),
    path("siklus-murid/", views.lifecycle, name="lifecycle"),
    path("siklus-murid/ekspor/", v.export_lifecycle, name="lifecycle_export"),
    path("siklus-murid/ekspor-kpi/", v.export_lifecycle_kpi, name="lifecycle_kpi_export"),
    path("kesehatan-bisnis/", v.business_health, name="health"),
    path("keuangan/", v.finance_control, name="finance"),
    path("nota/", v.nota, name="nota"),
    path("nota/arsip/<int:pk>/", v.nota_view, name="nota_view"),
    path("nota/<str:std>/<str:per>/", v.nota_preview, name="nota_preview"),
    path("nota/<str:std>/<str:per>/terbitkan/", v.nota_issue, name="nota_issue"),
    path("operasional/", v.operational, name="operations"),
    path("kesehatan-data/", v.data_health_view, name="data"),
    path("laporan/", v.reports, name="reports"),
    path("laporan/bulanan/", v.report_monthly, name="report_monthly"),
]
