from django.contrib.auth import views as auth_views
from django.urls import path

from . import views_admin

app_name = "accounts"
urlpatterns = [
    path("keluar/", auth_views.LogoutView.as_view(), name="logout"),
    path("pengguna/", views_admin.users_view, name="users"),
    path("pengguna/<int:membership_id>/cabut/", views_admin.revoke_view, name="revoke"),
]
