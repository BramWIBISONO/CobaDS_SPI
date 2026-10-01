import datetime

import pytest
from django.db import IntegrityError

from branches.models import Branch, BranchSetting, Membership


def test_unit_id_follows_the_branch_id():
    assert Branch(code="SPI-AS").unit_id == "UNIT-AS"
    assert Branch(code="SPI-JKT").unit_id == "UNIT-JKT"
    assert Branch(code="BDG").unit_id == "UNIT-BDG"


@pytest.mark.django_db
def test_one_membership_per_user_and_branch(branch, make_user):
    user = make_user("cso@spi.test", role="CSO", branch=branch)
    with pytest.raises(IntegrityError):
        Membership.objects.create(user=user, branch=branch, role="FINANCE")


@pytest.mark.parametrize("raw, expected", [
    (4, {"value_text": "", "value_number": 4.0, "value_date": None}),
    (datetime.datetime(2026, 10, 1, 0, 0), {"value_text": "", "value_number": None, "value_date": datetime.date(2026, 10, 1)}),
    ("SPI Jakarta", {"value_text": "SPI Jakarta", "value_number": None, "value_date": None}),
    (None, {"value_text": "", "value_number": None, "value_date": None}),
])
def test_setting_value_is_split_by_type(raw, expected):
    assert BranchSetting.split_value(raw) == expected


@pytest.mark.django_db
def test_setting_value_reads_back(branch):
    s = BranchSetting.objects.create(branch=branch, key="off_lama", **BranchSetting.split_value(3))
    assert s.value == 3.0
