from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views, views_admin

app_name = "accounts"
urlpatterns = [
    path("masuk/", views.login_view, name="login"),
    path("keluar/", auth_views.LogoutView.as_view(), name="logout"),
    path("daftar/", views.signup_view, name="signup"),
    path("daftar/terkirim/", views.signup_done_view, name="signup_done"),
    path("verifikasi/kirim-ulang/", views.resend_view, name="resend"),
    path("verifikasi/<uidb64>/<token>/", views.verify_view, name="verify"),
    path("lupa-password/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset_form.html", email_template_name="accounts/email/reset_body.txt",
        subject_template_name="accounts/email/reset_subject.txt", success_url=reverse_lazy("accounts:password_reset_done")),
        name="password_reset"),
    path("lupa-password/terkirim/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
         name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html", success_url=reverse_lazy("accounts:password_reset_complete")),
        name="password_reset_confirm"),
    path("reset/selesai/", auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
         name="password_reset_complete"),
    path("pengguna/", views_admin.users_view, name="users"),
    path("pengguna/<int:membership_id>/cabut/", views_admin.revoke_view, name="revoke"),
]
