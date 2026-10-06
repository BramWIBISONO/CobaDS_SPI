from django.urls import path

from . import views

app_name = "akademik"
urlpatterns = [
    path("final-project/", views.daftar, name="list"),
    path("final-project/murid/<str:std>/", views.ajukan, name="ajukan"),
    path("final-project/<int:pk>/", views.detail, name="detail"),
    path("final-project/<int:pk>/setujui/", views.setujui, name="setujui"),
    path("final-project/<int:pk>/tolak/", views.tolak, name="tolak"),
    path("final-project/<int:pk>/buat-sertifikat/", views.buat_ulang, name="buat_ulang"),
    path("final-project/<int:pk>/sertifikat.<str:fmt>", views.sertifikat, name="sertifikat"),
    path("final-project/<int:pk>/student-report/", views.rapor, name="rapor"),
]
