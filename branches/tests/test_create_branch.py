import re

import pytest

from audit.models import AuditLog, ImportLog
from branches.models import BranchSetting
from branches.services import create_branch
from importer.schema import load_schema
from masterdata.models import UnitMaster


@pytest.mark.django_db
def test_new_branch_gets_the_spi_configuration_and_no_operational_data(make_user):
    boss = make_user("boss@spi.test", super_admin=True)
    branch = create_branch(code="spi-bsd", name="SPI BSD", city="Tangerang Selatan", user=boss)
    assert (branch.code, branch.unit_id, branch.status) == ("SPI-BSD", "UNIT-BSD", "NEW_BRANCH")
    counts = {s.sheet: s.model_class().objects.for_branch(branch).count() for s in load_schema()}
    assert {s: n for s, n in counts.items() if n} == {"PROGRAM_MASTER": 16, "OFF_REASON_MASTER": 17, "UNIT_MASTER": 2,
                                                      "TARIF_FEE": 40, "IMPORT_LOG": 1, "AUDIT_LOG": 1}
    unit = UnitMaster.objects.for_branch(branch).get(uid="UNIT-BSD")
    assert (unit.name, unit.city, unit.status, unit.parent) == ("SPI BSD", "Tangerang Selatan", "NEW_BRANCH", "UNIT-HQ")
    batch = ImportLog.objects.for_branch(branch).get().batch
    assert re.fullmatch(r"IMP-BSD-\d{8}-01", batch)
    settings = {s.key: s.value for s in BranchSetting.objects.filter(branch=branch)}
    assert len(settings) == 23 and settings["batch"] == batch
    assert (settings["F"], settings["S"], settings["off_lama"], settings["ambang"]) == (1.0, 20.0, 3.0, 20000000.0)
    log = AuditLog.objects.for_branch(branch).get()
    assert (log.lid, log.action, log.entity, log.eid, log.user) == ("LOG-000001", "CREATE", "CABANG", "SPI-BSD", "Boss")


@pytest.mark.django_db
def test_branches_created_from_the_template_are_independent():
    one = create_branch(code="SPI-AA", name="SPI AA")
    two = create_branch(code="SPI-BB", name="SPI BB")
    assert UnitMaster.objects.for_branch(one).filter(uid="UNIT-BB").count() == 0
    assert set(UnitMaster.objects.for_branch(two).values_list("uid", flat=True)) == {"UNIT-BB", "UNIT-HQ"}
