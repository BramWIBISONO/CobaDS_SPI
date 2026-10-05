import pytest

from core.capabilities import ALL_CAPS, ROLE_CAPS, Cap, caps_for, role_of

# spesifikasi §9 - (kemampuan, peran yang boleh)
MATRIX = [
    (Cap.MANAGE_ALL, set()),
    (Cap.BRANCH_ADMIN, {"BRANCH_ADMIN"}),
    (Cap.VIEW, {"BRANCH_ADMIN", "MANAGER", "CSO", "FINANCE", "ACADEMIC"}),
    (Cap.STUDENT_WRITE, {"BRANCH_ADMIN", "MANAGER", "CSO"}),
    (Cap.DOCUMENT_WRITE, {"BRANCH_ADMIN", "MANAGER", "CSO", "ACADEMIC"}),
    (Cap.STATUS_CHANGE, {"BRANCH_ADMIN", "MANAGER", "CSO"}),
    (Cap.PAYMENT_EVIDENCE, {"BRANCH_ADMIN", "CSO", "FINANCE"}),
    (Cap.FINANCE_VERIFY, {"BRANCH_ADMIN", "FINANCE"}),
    (Cap.PERIOD_OPEN, {"BRANCH_ADMIN", "MANAGER", "FINANCE"}),
    (Cap.PERIOD_CLOSE, {"BRANCH_ADMIN", "MANAGER"}),
    (Cap.CLASS_WRITE, {"BRANCH_ADMIN", "MANAGER", "CSO", "ACADEMIC"}),
    (Cap.ACADEMIC_WRITE, {"BRANCH_ADMIN", "MANAGER", "ACADEMIC"}),
    (Cap.SESSION_WRITE, {"BRANCH_ADMIN", "MANAGER", "CSO", "ACADEMIC"}),
    (Cap.SESSION_WRITE_OWN, {"BRANCH_ADMIN", "TEACHER"}),
    (Cap.SEE_CONTACTS, {"BRANCH_ADMIN", "MANAGER", "CSO", "FINANCE"}),
    (Cap.DATA_VALIDATE, {"BRANCH_ADMIN", "MANAGER", "CSO", "FINANCE", "ACADEMIC"}),
    (Cap.AUDIT_VIEW, {"BRANCH_ADMIN", "MANAGER"}),
]


@pytest.mark.parametrize("cap, roles", MATRIX)
def test_role_matrix_matches_the_spec(cap, roles):
    assert {r for r, caps in ROLE_CAPS.items() if cap in caps} == roles


def test_matrix_covers_every_capability():
    assert {c for c, _ in MATRIX} == set(ALL_CAPS)


@pytest.mark.django_db
def test_super_admin_has_everything_in_every_branch(branch, other_branch, make_user):
    boss = make_user("boss@spi.test", super_admin=True)
    assert role_of(boss, other_branch) == "SUPER_ADMIN"
    assert caps_for(boss, branch) == ALL_CAPS


@pytest.mark.django_db
def test_a_role_only_counts_in_its_own_branch(branch, other_branch, make_user):
    cso = make_user("cso@spi.test", role="CSO", branch=branch)
    assert Cap.STUDENT_WRITE in caps_for(cso, branch)
    assert caps_for(cso, other_branch) == frozenset()
    assert role_of(cso, other_branch) is None


@pytest.mark.django_db
def test_user_without_membership_or_branch_has_nothing(branch, make_user):
    newbie = make_user("baru@spi.test")
    assert caps_for(newbie, branch) == frozenset()
    assert caps_for(newbie, None) == frozenset()
