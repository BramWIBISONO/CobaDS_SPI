# Izin dan peran

DIBANGKITKAN dari `core/permissions.py` + `core/capabilities.py` oleh `manage.py permissions_doc` - jangan diedit tangan.
Setiap aksi dicek di server (`require_perm`); menyembunyikan tombol bukan pengaman.
Super Admin memiliki semua izin di semua cabang. Staff = CSO, Management = Manager.

| Izin | Kemampuan | Branch Admin | Manager | CSO | Finance | Academic | Teacher |
|---|---|---|---|---|---|---|---|
| `student.view` | view | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| `student.create` | student_write | ✓ | ✓ | ✓ | – | – | – |
| `student.edit` | student_write | ✓ | ✓ | ✓ | – | – | – |
| `student.status` | status_change | ✓ | ✓ | ✓ | – | – | – |
| `student.contacts` | see_contacts | ✓ | ✓ | ✓ | ✓ | – | – |
| `parent.view` | view | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| `parent.edit` | student_write | ✓ | ✓ | ✓ | – | – | – |
| `class.view` | view | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| `class.manage` | class_write | ✓ | ✓ | ✓ | – | ✓ | – |
| `class.over_capacity` | branch_admin | ✓ | – | – | – | – | – |
| `teacher.view` | view | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| `teacher.manage` | class_write | ✓ | ✓ | ✓ | – | ✓ | – |
| `session.view` | view | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| `session.manage` | session_write | ✓ | ✓ | ✓ | – | ✓ | – |
| `session.own` | session_write_own | ✓ | – | – | – | – | ✓ |
| `attendance.manage` | session_write | ✓ | ✓ | ✓ | – | ✓ | – |
| `attendance.own` | session_write_own | ✓ | – | – | – | – | ✓ |
| `academic.manage` | academic_write | ✓ | ✓ | – | – | ✓ | – |
| `finance.view` | view | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| `payment.record` | payment_evidence | ✓ | – | ✓ | ✓ | – | – |
| `payment.verify` | finance_verify | ✓ | – | – | ✓ | – | – |
| `billing.decide` | finance_verify | ✓ | – | – | ✓ | – | – |
| `period.open` | period_open | ✓ | ✓ | – | ✓ | – | – |
| `period.close` | period_close | ✓ | ✓ | – | – | – | – |
| `off.manage` | status_change | ✓ | ✓ | ✓ | – | – | – |
| `followup.manage` | student_write | ✓ | ✓ | ✓ | – | – | – |
| `report.view` | view | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| `report.export` | view | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| `user.manage` | branch_admin | ✓ | – | – | – | – | – |
| `settings.manage` | branch_admin | ✓ | – | – | – | – | – |
| `import.run` | branch_admin | ✓ | – | – | – | – | – |
| `audit.view` | audit_view | ✓ | ✓ | – | – | – | – |
| `branch.manage` | manage_all | – | – | – | – | – | – |
| `management.view` | management | ✓ | ✓ | – | – | – | – |
| `management.finance` | finance_control | ✓ | ✓ | – | ✓ | – | – |
| `nota.issue` | finance_verify | ✓ | – | – | ✓ | – | – |
