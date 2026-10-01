"""Pemeriksaan sebelum impor: kolom wajib, tipe nilai, ID ganda, rujukan, murid kembar, dan unit cabang."""
from dataclasses import asdict, dataclass

from .convert import ConvertError, convert
from .schema import load_schema, table


@dataclass
class Issue:
    level: str
    table: str
    row: int | None
    field: str
    message: str

    def as_dict(self):
        return asdict(self)


# (tabel, kolom, tabel tujuan, kolom tujuan, tingkat): nilai yang terisi harus ada di tabel tujuan
REFERENCE_RULES = (
    ("STATUS_EVENT", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("SPP_TAGIHAN", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("BUKTI_BAYAR", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("ACADEMIC_RECORD", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("DOKUMEN", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("FOLLOW_UP", "Student ID", "STUDENT_MASTER", "Student ID", "error"),
    ("FOLLOW_UP", "Lead ID", "LEAD", "Lead ID", "error"),
    ("LEAD", "Student ID (konversi)", "STUDENT_MASTER", "Student ID", "warning"),
    ("STUDENT_MASTER", "Parent ID", "PARENT_MASTER", "Parent ID", "warning"),
    ("STUDENT_OFF", "Student ID", "STUDENT_MASTER", "Student ID", "warning"),
    ("CLASS_MEMBERS", "Student ID", "STUDENT_MASTER", "Student ID", "warning"),
    ("SESI", "Slot Jadwal", "CLASS_SCHEDULE", "Schedule ID", "warning"),
    ("D_BULAN", "Student ID", "STUDENT_MASTER", "Student ID", "warning"),
)


def _values(data, sheet, name):
    return {str(r.values.get(name)) for r in data.tables.get(sheet, []) if r.values.get(name) not in (None, "")}


def validate(data, branch=None):
    issues = []
    for sheet, headers in data.missing_headers.items():
        issues += [Issue("error", sheet, None, h, f"Kolom '{h}' tidak ada di sheet {sheet}.") for h in headers]
    for spec in load_schema():
        seen = {}
        for r in data.tables.get(spec.sheet, []):
            for f in spec.stored_fields:
                if f.name in r.values:
                    try:
                        convert(f, r.values[f.name])
                    except ConvertError as exc:
                        issues.append(Issue("error", spec.sheet, r.row, f.header, str(exc)))
            key = r.values.get(spec.key)
            if spec.unique:
                if key in seen:
                    issues.append(Issue("error", spec.sheet, r.row, spec.field_by_name[spec.key].header,
                                        f"ID ganda '{key}' (juga di baris {seen[key]})."))
                else:
                    seen[key] = r.row
    for sheet, header, target, target_header, level in REFERENCE_RULES:
        f = table(sheet).field_by_header[header]
        known = _values(data, target, table(target).field_by_header[target_header].name)
        for r in data.tables.get(sheet, []):
            v = r.values.get(f.name)
            if v not in (None, "") and str(v) not in known:
                issues.append(Issue(level, sheet, r.row, header, f"'{v}' tidak ada di {target} ({target_header})."))
    issues += _twin_students(data)
    if branch is not None:
        issues += _branch_check(data, branch)
    return issues


def _twin_students(data):
    spec = table("STUDENT_MASTER")
    name_f, birth_f = spec.field_by_header["Nama Murid"], spec.field_by_header["Tanggal Lahir"]
    seen, out = {}, []
    for r in data.tables.get("STUDENT_MASTER", []):
        name, birth = r.values.get(name_f.name), r.values.get(birth_f.name)
        if name in (None, "") or birth in (None, ""):
            continue
        key = (str(name).strip().lower(), str(birth)[:10])
        if key in seen:
            out.append(Issue("warning", "STUDENT_MASTER", r.row, "Nama Murid",
                             f"Nama & tanggal lahir sama dengan baris {seen[key]} - pastikan bukan murid yang sama."))
        else:
            seen[key] = r.row
    return out


def _branch_check(data, branch):
    out = []
    code = data.setting("branch_id")
    if code and code["value"] and str(code["value"]).strip().upper() != branch.code.upper():
        out.append(Issue("error", "SETTINGS", code["row"], "Branch ID",
                         f"Workbook ini milik cabang {code['value']}, bukan {branch.code}. Data cabang lain tidak boleh diimpor."))
    unit = data.unit
    if not unit:
        out.append(Issue("warning", "SETTINGS", None, "Unit", f"Unit workbook tidak tercatat - pastikan workbook ini milik {branch.name}."))
    elif unit != branch.unit_id:
        out.append(Issue("error", "SETTINGS", None, "Unit",
                         f"Workbook ini milik unit {unit}, bukan {branch.unit_id} ({branch.name}). Data cabang lain tidak boleh diimpor."))
    return out
