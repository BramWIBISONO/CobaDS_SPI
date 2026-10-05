from django.urls import path

from . import views

app_name = "students"
urlpatterns = [
    path("murid/", views.student_list, name="list"),
    path("murid/baru/", views.student_create, name="create"),
    path("murid/ekspor/", views.student_export, name="export"),
    path("murid/aksi-massal/", views.student_bulk, name="bulk"),
    path("murid/<str:std>/", views.student_detail, name="detail"),
    path("murid/<str:std>/ubah/", views.student_edit, name="edit"),
    path("murid/<str:std>/status/", views.student_status, name="status"),
    path("murid/<str:std>/kelas/", views.student_class, name="class"),
    path("murid/<str:std>/catatan/", views.student_note, name="note"),
    path("orang-tua/", views.parent_list, name="parents"),
    path("orang-tua/baru/", views.parent_create, name="parent_create"),
    path("orang-tua/<str:pid>/", views.parent_detail, name="parent_detail"),
    path("orang-tua/<str:pid>/ubah/", views.parent_edit, name="parent_edit"),
    path("orang-tua/<str:pid>/anak/", views.parent_link, name="parent_link"),
    path("orang-tua/<str:pid>/komunikasi/", views.parent_note, name="parent_note"),
    path("follow-up/", views.followup_list, name="followups"),
    path("follow-up/baru/", views.followup_create, name="followup_create"),
    path("follow-up/<str:fid>/", views.followup_detail, name="followup_detail"),
]
