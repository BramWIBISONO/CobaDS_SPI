from django.db import models

from importer.schema import load_schema, table

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
