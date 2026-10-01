import pytest
from django.urls import reverse

from audit.models import AuditLog
from branches.models import Membership


@pytest.mark.django_db
def test_only_branch_admin_opens_the_users_page(client, branch, make_user):
    client.force_login(make_user("cso@spi.test", role="CSO", branch=branch))
    assert client.get(reverse("accounts:users")).status_code == 403


@pytest.mark.django_db
def test_branch_admin_grants_a_role_and_it_is_audited(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    newbie = make_user("baru@spi.test")
    page = client.get(reverse("accounts:users")).content.decode()
    assert "baru@spi.test" in page                                     # daftar menunggu akses
    response = client.post(reverse("accounts:users"), {"email": "BARU@spi.test", "role": "FINANCE"})
    assert response.status_code == 302
    assert Membership.objects.get(user=newbie, branch=branch).role == "FINANCE"
    log = AuditLog.objects.for_branch(branch).get()
    assert (log.action, log.entity, log.eid, log.new) == ("ACCESS", "PENGGUNA", "baru@spi.test", "FINANCE")


@pytest.mark.django_db
def test_unverified_or_unknown_email_cannot_be_granted(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    make_user("belum@spi.test", active=False)
    for email in ("belum@spi.test", "tidakada@spi.test"):
        response = client.post(reverse("accounts:users"), {"email": email, "role": "CSO"})
        assert response.status_code == 200 and "Tidak ada pengguna aktif" in response.content.decode()
    assert Membership.objects.filter(branch=branch).count() == 1


@pytest.mark.django_db
def test_teacher_role_needs_the_teacher_name(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    make_user("guru@spi.test")
    response = client.post(reverse("accounts:users"), {"email": "guru@spi.test", "role": "TEACHER"})
    assert "Isi nama guru" in response.content.decode()


@pytest.mark.django_db
def test_revoking_a_membership_of_another_branch_is_not_found(client, branch, other_branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    foreign = Membership.objects.create(user=make_user("x@spi.test"), branch=other_branch, role="CSO")
    assert client.post(reverse("accounts:revoke", args=[foreign.pk])).status_code == 404
    assert Membership.objects.filter(pk=foreign.pk).exists()


@pytest.mark.django_db
def test_revoke_in_own_branch_removes_and_audits(client, branch, make_user):
    client.force_login(make_user("admin@spi.test", role="BRANCH_ADMIN", branch=branch))
    member = Membership.objects.create(user=make_user("cso@spi.test"), branch=branch, role="CSO")
    assert client.post(reverse("accounts:revoke", args=[member.pk])).status_code == 302
    assert not Membership.objects.filter(pk=member.pk).exists()
    assert AuditLog.objects.for_branch(branch).get().new == "(dicabut)"
