from django.urls import path

from . import views

app_name = "masterdata"
urlpatterns = [
    path("guru/", views.teacher_list, name="teachers"),
    path("guru/baru/", views.teacher_create, name="teacher_create"),
    path("guru/<str:tid>/", views.teacher_detail, name="teacher"),
    path("guru/<str:tid>/ubah/", views.teacher_edit, name="teacher_edit"),
]
