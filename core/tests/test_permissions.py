import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from core.capabilities import ROLE_CAPS, Cap
from core.permissions import PERMISSIONS, PermSet, has_perm, perms_for_role, require_perm


def test_every_named_permission_maps_to_a_capability():
    assert PERMISSIONS and all(isinstance(cap, Cap) for cap in PERMISSIONS.values())
    for name in ("student.view", "student.create", "student.edit", "student.status", "class.manage", "attendance.manage",
                 "session.manage", "finance.view", "payment.record", "payment.verify", "off.manage", "followup.manage",
                 "report.view", "report.export", "user.manage", "settings.manage", "audit.view"):
        assert name in PERMISSIONS, name


def test_roles_get_the_expected_permissions():
    teacher, finance, cso, manager = (perms_for_role(r) for r in ("TEACHER", "FINANCE", "CSO", "MANAGER"))
    assert teacher == {"session.own", "attendance.own"}
    assert "payment.verify" in finance and "student.edit" not in finance
    assert {"student.create", "student.status", "payment.record", "followup.manage"} <= cso and "payment.verify" not in cso
    assert "audit.view" in manager and "user.manage" not in manager
    assert perms_for_role("BRANCH_ADMIN") >= set(PERMISSIONS) - {"branch.manage"}
    assert Cap.AUDIT_VIEW in ROLE_CAPS["BRANCH_ADMIN"]


def test_template_perm_object_reads_dotted_names_with_underscores():
    p = PermSet({"student.edit"})
    assert p.student_edit is True and p.payment_verify is False and "student.edit" in p


def test_unknown_permission_is_a_programming_error():
    with pytest.raises(KeyError):
        require_perm("tidak.ada")


@pytest.mark.django_db
def test_require_perm_blocks_on_the_server(branch, make_user):
    rf = RequestFactory()

    @require_perm("payment.verify")
    def view(request):
        return HttpResponse("ok")

    request = rf.get("/x/")
    request.user, request.branch = make_user("cso@spi.test", role="CSO", branch=branch), branch
    request.caps = ROLE_CAPS["CSO"]
    assert view(request).status_code == 403 and not has_perm(request, "payment.verify")
    request.caps = ROLE_CAPS["FINANCE"]
    assert view(request).status_code == 200 and has_perm(request, "payment.verify")
