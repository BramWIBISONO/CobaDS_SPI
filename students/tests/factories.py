"""Data kecil untuk uji modul murid / kelas / keuangan."""
import datetime

from classes.models import ClassMaster, ClassMembers
from finance.models import Periode
from masterdata.models import ProgramMaster, TeacherMaster
from students.models import ParentMaster, StudentMaster


def seed_branch(branch):
    TeacherMaster.objects.create(branch=branch, row_no=1, tid="TCH-001", name="Mr. Bram", status="ACTIVE")
    TeacherMaster.objects.create(branch=branch, row_no=2, tid="TCH-002", name="Ms. Linda", status="ACTIVE")
    ProgramMaster.objects.create(branch=branch, row_no=1, pid="PRG-F10", program="Foundation", level="Foundation 1.0", status="ACTIVE")
    ProgramMaster.objects.create(branch=branch, row_no=2, pid="PRG-D21", program="Development", level="Development 2.1", status="ACTIVE")
    ClassMaster.objects.create(branch=branch, row_no=1, class_id="CLS-P001", code="P001", tipe="Partner", program="Development",
                               level="Development 2.1", guru="Mr. Bram", mode="OnSite")
    ClassMaster.objects.create(branch=branch, row_no=2, class_id="CLS-F002", code="F002", tipe="Focus", program="Foundation",
                               level="Foundation 1.0", guru="Ms. Linda", mode="OnLine")
    ParentMaster.objects.create(branch=branch, row_no=1, pid="PAR-00001", nama="Ibu Sari", wa="0812000001", email="sari@contoh.id")
    StudentMaster.objects.create(branch=branch, row_no=1, std="STD-000001", nama="Ani Wijaya", st_base="ACTIVE", kode_read="P001",
                                 guru="Mr. Bram", program="Development", level="Development 2.1", par="PAR-00001", hp="0813111",
                                 harga=650000, mode="OnSite", join=datetime.date(2024, 1, 10))
    StudentMaster.objects.create(branch=branch, row_no=2, std="STD-000002", nama="Budi Santoso", st_base="OFF", kode_read="F002",
                                 guru="Ms. Linda", program="Foundation", level="Foundation 1.0", mode="OnLine")
    ClassMembers.objects.create(branch=branch, row_no=1, mbr="MBR-0001", code="P001", class_id="CLS-P001", std="STD-000001",
                                status="CURRENT", start=datetime.date(2024, 1, 1))


def open_period(branch, per="2026-10", status="OPEN"):
    y, m = map(int, per.split("-"))
    return Periode.objects.create(branch=branch, row_no=Periode.objects.filter(branch=branch).count() + 1, per=per,
                                  label=per, mulai=datetime.date(y, m, 1), status=status)
