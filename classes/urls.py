from django.urls import path

from . import views

app_name = "classes"
urlpatterns = [
    path("kelas/", views.class_list, name="list"),
    path("kelas/baru/", views.class_create, name="create"),
    path("kelas/jadwal/<str:sid>/akhiri/", views.end_slot, name="end_slot"),
    path("kelas/<str:code>/", views.class_detail, name="detail"),
    path("kelas/<str:code>/ubah/", views.class_edit, name="edit"),
    path("kelas/<str:code>/guru/", views.assign_teacher, name="assign_teacher"),
    path("kelas/<str:code>/murid/", views.add_member, name="add_member"),
    path("kelas/<str:code>/jadwal/", views.add_slot, name="add_slot"),
    path("kelas/<str:code>/tutup/", views.close_class, name="close"),
    path("sesi/", views.session_list, name="sessions"),
    path("sesi/buat/", views.generate, name="generate"),
    path("sesi/<str:sid>/", views.session_detail, name="session"),
    path("jadwal-saya/", views.my_sessions, name="my_sessions"),
]
