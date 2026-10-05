import pytest
from django.urls import reverse

from core.models import Notifikasi
from core.notifications import notify, unread_count


@pytest.mark.django_db
def test_notifications_are_per_user_and_branch(client, branch, other_branch, make_user):
    ani, budi = make_user("ani@spi.test", role="CSO", branch=branch), make_user("budi@spi.test", role="CSO", branch=branch)
    notify(ani, branch, "Follow-up jatuh tempo", "FU-000001 untuk STD-000001", url="/follow-up/")
    notify(ani, other_branch, "Cabang lain", "")
    assert unread_count(ani, branch) == 1 and unread_count(budi, branch) == 0
    client.force_login(ani)
    page = client.get(reverse("core:notifikasi")).content.decode()
    assert "Follow-up jatuh tempo" in page and "Cabang lain" not in page
    assert 'data-notif-count="1"' in client.get("/").content.decode()
    n = Notifikasi.objects.get(title="Follow-up jatuh tempo")
    response = client.post(reverse("core:notifikasi_baca", args=[n.pk]))
    assert response.status_code == 302 and response.url == "/follow-up/" and unread_count(ani, branch) == 0


@pytest.mark.django_db
def test_a_user_cannot_read_someone_elses_notification(client, branch, make_user):
    ani, budi = make_user("ani@spi.test", role="CSO", branch=branch), make_user("budi@spi.test", role="CSO", branch=branch)
    n = notify(ani, branch, "Rahasia", "")
    client.force_login(budi)
    assert client.post(reverse("core:notifikasi_baca", args=[n.pk])).status_code == 404
