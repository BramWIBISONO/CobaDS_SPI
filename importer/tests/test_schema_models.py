from django.db import models

from importer.schema import load_schema, table
from tools.generate_models import MONEY_FIELDS

KIND_FIELD = {"text": models.TextField, "number": models.FloatField, "date": models.DateField,
              "datetime": models.DateTimeField, "time": models.TimeField, "bool": models.BooleanField}


def test_34_tables_without_settings():
    sheets = [t.sheet for t in load_schema()]
    assert len(sheets) == 34 and "SETTINGS" not in sheets
    assert {"D_BULAN", "D_MURID", "STUDENT_MASTER", "SPP_TAGIHAN", "BUKU_KAS", "AUDIT_LOG"} <= set(sheets)


def test_every_table_has_a_model_with_exactly_its_stored_fields():
    for t in load_schema():
        names = {f.name for f in t.model_class()._meta.get_fields()}
        for f in t.fields:
            assert (f.name in names) == f.stored, (t.sheet, f.header)
            if f.text_field:
                assert f.text_field in names, (t.sheet, f.header)


def test_field_types_follow_the_schema():
    for t in load_schema():
        M = t.model_class()
        for f in t.stored_fields:
            field = M._meta.get_field(f.name)
            expected = models.CharField if (f.name == t.key and f.kind == "text") else KIND_FIELD[f.kind]
            if (t.sheet, f.name) in MONEY_FIELDS:
                expected = models.DecimalField                 # uang tabel transaksi (docs/ARCHITECTURE.md A3)
            assert isinstance(field, expected), (t.sheet, f.header, type(field))


def test_business_key_is_unique_per_branch():
    for t in load_schema():
        uniques = [tuple(c.fields) for c in t.model_class()._meta.constraints]
        assert (("branch", t.key) in uniques) == t.unique, t.sheet
    assert table("IMPORT_LOG").unique is False


def test_mixed_and_formula_columns():
    sm = table("STUDENT_MASTER").field_by_header
    assert sm["Harga SPP"].kind == "number" and sm["Harga SPP"].text_field
    assert sm["Join"].text_field
    assert sm["Status Sekarang"].stored is False
    assert table("SPP_TAGIHAN").field_by_header["Status Pembayaran"].stored is False
    assert table("SESI").field_by_header["Murid Hadir"].kind == "number"


def test_simulation_sheet_is_a_fixed_block():
    sim = table("SIMULASI_JADWAL")
    assert sim.skip_key_only and sim.stop_at_blank
    assert not any(t.stop_at_blank for t in load_schema() if t.sheet != "SIMULASI_JADWAL")


def test_cash_book_counted_flag_is_stored():
    # Dihitung = nilai tetap di semua baris kecuali Agustus 2026 (rumus pilihan jurnal) -> harus ikut diimpor
    assert table("BUKU_KAS").field_by_header["Dihitung"].stored is True


def test_money_columns_of_transaction_tables_are_decimal():
    from finance.models import BuktiBayar, SppTagihan
    from students.models import StudentMaster

    for model, name in ((SppTagihan, "harga"), (SppTagihan, "diskon"), (SppTagihan, "adj"), (BuktiBayar, "nominal"),
                        (StudentMaster, "harga"), (StudentMaster, "harga_in")):
        field = model._meta.get_field(name)
        assert isinstance(field, models.DecimalField) and (field.max_digits, field.decimal_places) == (14, 2), (model, name)


def test_follow_up_has_app_task_columns():
    from students.models import FollowUp

    names = {f.name for f in FollowUp._meta.get_fields()}
    assert {"prioritas", "ditugaskan", "selesai_pada", "diubah_pada"} <= names
    assert FollowUp._meta.get_field("ditugaskan").related_model.__name__ == "User"
    assert "prioritas" not in {f.name for f in table("FOLLOW_UP").stored_fields}      # kolom aplikasi: tidak diimpor
