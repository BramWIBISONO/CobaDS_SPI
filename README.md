# SPI Management — aplikasi web

Aplikasi web SPI yang mengikuti aplikasi Excel v4 (`..\APP\*.xlsm`): tabel, ID, aturan, dan alur yang sama, dengan antarmuka web.
Spesifikasi: `docs/superpowers/specs/2026-09-30-spi-web-design.md` · rencana: `docs/superpowers/plans/`.

## Status

Tahap 1A (fondasi) selesai: 34 tabel Excel v4 sebagai model per cabang (kolom rumus tidak disimpan), login dengan verifikasi email,
lupa/reset password, peran per cabang dan isolasi data cabang, penomoran ID & AUDIT_LOG seperti VBA, impor workbook v4
(pratinjau → simpan), dan cabang baru dari template. Berikutnya: tahap 1B (perhitungan + HOME / MURID / PROFIL setara Excel),
tahap 2 (operasional: form, SPP, kelas, akademik, OFF), tahap 3 (manajemen, admin, deploy).

## Menyiapkan (Windows, Git Bash, dari folder `app web`)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
npm install && npm run vendor && npm run build:css
cp .env.example .env            # lalu isi SECRET_KEY acak (lihat rencana Task 1)
.venv/Scripts/python scripts/devdb.py start      # PostgreSQL lokal (pgserver), menulis DATABASE_URL ke .env
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py createcachetable
.venv/Scripts/python manage.py runserver
```

Super admin pertama: `.venv/Scripts/python manage.py createsuperuser`. Email dikirim ke konsol server selama `EMAIL_BACKEND` konsol.

Bila komputer mati tanpa `devdb.py stop`, PostgreSQL memulihkan datanya sekitar 1 menit saat `devdb.py start`; jalankan lagi
bila diminta. Data zona waktu PostgreSQL disalin otomatis dari paket `tzdata` (build Windows pgserver tidak membawanya).

## Migrasi data dari Excel

Workbook di `..\APP` hanya dibaca. Tanpa `--commit` perintah hanya menampilkan pratinjau (jumlah baris, error, peringatan).

```bash
.venv/Scripts/python manage.py import_workbook "../APP/SPI_STUDENT-SPP_APP_2026_09_v4.xlsm" --branch SPI-JKT --create --name "SPI Jakarta" --city Jakarta --status ACTIVE --commit
.venv/Scripts/python manage.py import_workbook "../APP/SPI_ALAM_SUTERA_v4.xlsm" --branch SPI-AS --create --commit
```

- Migrasi awal cabang yang sudah punya workbook: pakai perintah ini dengan `--create`, supaya semua ID Excel (termasuk Log ID) tetap sama.
- Impor ke cabang yang sudah berisi data hanya dengan `--replace` (di web: centang "ganti semua data cabang"). Isi tabel diganti;
  AUDIT_LOG dan IMPORT_LOG tidak pernah dihapus, dan baris riwayat yang sama tidak ditambahkan dua kali.
- Workbook cabang lain (Unit / Branch ID berbeda), workbook v1–v3, atau file bukan Excel ditolak.
- Cabang baru tanpa workbook: menu Admin → Cabang (super admin). Konfigurasi SPI disalin dari `branches/template_config.json`
  (hasil `tools/export_template_config.py` dari `SPI_BRANCH_TEMPLATE_v4.xlsm`).

## Uji

```bash
.venv/Scripts/python -m pytest              # uji cepat
.venv/Scripts/python -m pytest -m slow      # memakai workbook asli di ..\APP: jumlah baris & setiap sel Jakarta, Alam Sutera, template
```

## Alat pengembang (jalankan ulang hanya bila pipeline Excel berubah)

- `tools/export_schema.py` → `importer/schema/excel_tables.json` (definisi tabel dari `v2_layout.py`)
- `tools/generate_models.py` → `<app>/models_excel.py` (DIBANGKITKAN; lalu `makemigrations`)
- `tools/export_template_config.py` → `branches/template_config.json`

## Aturan yang dijaga

- Satu baris data = satu cabang; setiap halaman cabang mengecek peran di server.
- ID sama dengan Excel dan dibuat dalam transaksi dengan kunci cabang (tidak pernah ganda / dipakai ulang).
- Kontak tidak pernah ikut ekspor CSV (K2); tarif fee guru tidak dikarang (K3).
