import threading
import time

import pytest
from django.db import connection, transaction

from audit.models import AuditLog
from core import audit
from core.ids import next_id, next_row_no
from students.models import StudentMaster


@pytest.mark.django_db
def test_next_id_follows_the_largest_number_of_the_prefix(branch, other_branch):
    with transaction.atomic():
        assert next_id(StudentMaster, "std", "STD-", 6, branch) == "STD-000001"
    StudentMaster.objects.create(branch=branch, std="STD-000009", row_no=1)
    StudentMaster.objects.create(branch=branch, std="STD-00001X", row_no=2)       # bukan angka: diabaikan
    StudentMaster.objects.create(branch=branch, std="STD-0000000000123", row_no=3)  # >= 10 digit: diabaikan (seperti VBA)
    StudentMaster.objects.create(branch=other_branch, std="STD-000050", row_no=1)   # cabang lain: tidak dihitung
    with transaction.atomic():
        assert next_id(StudentMaster, "std", "STD-", 6, branch) == "STD-000010"


@pytest.mark.django_db(transaction=True)                     # uji biasa sudah dibungkus atomic oleh pytest-django
def test_next_id_refuses_to_run_outside_a_transaction(branch):
    with pytest.raises(RuntimeError):
        next_id(StudentMaster, "std", "STD-", 6, branch)


@pytest.mark.django_db
def test_next_row_no_appends_after_the_last_row(branch):
    assert next_row_no(StudentMaster, branch) == 1
    StudentMaster.objects.create(branch=branch, std="STD-000001", row_no=329)
    assert next_row_no(StudentMaster, branch) == 330


@pytest.mark.django_db(transaction=True)
def test_two_users_saving_at_once_get_different_ids(branch):
    barrier, results, errors = threading.Barrier(2), [], []

    def save_one():
        try:
            with transaction.atomic():
                barrier.wait(timeout=10)
                sid = next_id(StudentMaster, "std", "STD-", 6, branch)
                time.sleep(0.3)                                   # lebarkan jendela balapan
                StudentMaster.objects.create(branch=branch, std=sid, row_no=1)
                results.append(sid)
        except Exception as exc:                                  # noqa: BLE001 - dilaporkan oleh assert
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=save_one) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert errors == []
    assert sorted(results) == ["STD-000001", "STD-000002"]


@pytest.mark.django_db
def test_audit_log_numbers_rows_per_branch(branch, other_branch, make_user):
    user = make_user("admin@spi.test", full_name="Admin Uji")
    first = audit.log(branch=branch, user=user, action="CREATE", entity="STUDENT_MASTER", entity_id="STD-000001", new="Murid baru")
    second = audit.log(branch=branch, user=user, action="UPDATE", entity="STUDENT_MASTER", entity_id="STD-000001", field="Harga",
                       old=450000.0, new=500000.0)
    elsewhere = audit.log(branch=other_branch, user=None, action="CREATE", entity="CABANG", entity_id="SPI-AS")
    assert (first.lid, second.lid, elsewhere.lid) == ("LOG-000001", "LOG-000002", "LOG-000001")
    assert first.user == "Admin Uji" and first.by == "APLIKASI" and first.ts is not None
    assert (second.old, second.new) == ("450000", "500000")
    assert elsewhere.user == "sistem"
    assert AuditLog.objects.for_branch(branch).count() == 2
