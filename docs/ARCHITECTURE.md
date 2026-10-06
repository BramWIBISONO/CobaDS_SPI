# Arsitektur SPI Super App

Status: berlaku mulai 5 Okt 2026 (branch `super-app`). Dasar: fondasi tahap 1A + dasbor gelombang 1.
Arah produk: aplikasi ini adalah **sistem operasional utama** SPI. Database + logika backend = sumber kebenaran.
Workbook Excel di `..\APP` hanya acuan (data historis, aturan bisnis yang sudah dipelajari, regresi angka emas Wave 1).

## 1. Keputusan arsitektur

| No | Keputusan | Alasan | Konsekuensi |
|---|---|---|---|
| A1 | Tabel operasional v4 (`models_excel.py`: murid, orang tua, kelas, anggota, jadwal, sesi, event status, OFF, follow-up, akademik, lead, dokumen, tagihan, bukti bayar, periode, audit) tetap menjadi penyimpan domain. Aplikasi menulis ke tabel yang sama. | Desain relasional v4 sudah lengkap untuk siklus murid, berisi data historis Jakarta, dan seluruh perhitungan Wave 1 (status sekarang, OFF, kelas, SPP) langsung ikut benar. Menulis ulang = risiko besar tanpa nilai baru. | Nama tabel/kolom mengikuti v4. Halaman tidak meniru sheet: tiap modul punya alur aplikasi sendiri. |
| A2 | Relasi antar tabel v4 memakai **kunci bisnis per cabang** (Student ID, Parent ID, Kode Kelas, Sesi ID …), divalidasi di service; tabel baru buatan aplikasi memakai **ForeignKey** ke cabang & pengguna. | Baris v4 dapat diganti utuh oleh impor migrasi (PK berubah); kunci bisnis tetap. Semua pencarian selalu difilter cabang ⇒ kebocoran lintas cabang tidak mungkin. | Integritas referensi dijaga service + unique constraint `(branch, kunci)`. |
| A3 | Kolom milik aplikasi pada tabel v4 ditambahkan lewat `APP_FIELDS` di `tools/generate_models.py` (bukan edit tangan). Uang pada tabel transaksi memakai `DecimalField` (`MONEY_FIELDS`). | File model tetap dibangkitkan; impor mengabaikan kolom aplikasi. | Regenerasi model aman; migrasi ditambahkan normal. |
| A4 | Logika bisnis hanya di **service** (`<app>/services.py`, `dashboards/calc/*`). View = validasi form + panggil service + render. Template tidak menghitung. | Satu sumber perhitungan untuk halaman, laporan, API, uji. | Angka tidak pernah dibaca ulang dari teks HTML. |
| A5 | Setiap service yang menulis: `transaction.atomic`, ID lewat `core.ids.next_id`, satu baris `AUDIT_LOG` per perubahan (`core.audit.log`), nilai lama → baru. | Jejak audit seperti VBA v4; nomor tidak pernah dipakai dua kali. | Riwayat murid (timeline) dibaca dari AUDIT_LOG + tabel event. |
| A6 | Hak akses = **izin bernama** (`student.edit`, `payment.verify`, …) yang dipetakan ke kemampuan peran (`core/capabilities.py`), dicek di server (`require_perm`). Tombol disembunyikan hanya sebagai kenyamanan. | Satu matriks, dapat diuji. | `docs/PERMISSIONS.md` dibangkitkan dari kode. |
| A7 | Status murid: `ACTIVE`, `ON LEAVE`, `OFF`, `PENDING`, `ALUMNI/INACTIVE` (selesai/lulus). Perubahan status selalu lewat event (`STATUS_EVENT`) — tidak pernah menimpa kolom. | Riwayat status lengkap; mesin status Wave 1 (`status_sekarang`, status akhir periode) tetap berlaku. | Status sekarang = event terakhir ≤ hari ini, lalu status awal, lalu PENDING. |
| A8 | Periode operasional (BULAN BARU / TUTUP BULAN) menghasilkan tagihan SPP dan sesi dari jadwal resmi, tidak pernah dobel (ID deterministik `TAG-yyyymm-STD`, `SES-yyyymmdd-<slot>`). | Aturan v4 yang sudah disetujui pemilik. | Periode CLOSED menolak perubahan sesi/status/kehadiran. |
| A9 | Tabel baru: `Kehadiran` (per murid per sesi, unik), `CatatanMurid`, `Notifikasi`, `SecurityEvent` (masuk/keluar/gagal). | Konsep yang tidak ada di v4. | — |
| A10 | Front-end: Django template + HTMX + Alpine, komponen bersama (`templates/components/`) dan design system tunggal (`docs/DESIGN_SYSTEM.md`, `/ui-kit/`), Chart.js hanya di halaman bergrafik. | Progressive enhancement, JS minimal. | Semua aksi juga jalan tanpa JS (form biasa). |

## 2. Domain dan tabel

| Domain | Tabel (app) | Kunci | Service |
|---|---|---|---|
| Murid | `STUDENT_MASTER` (students) | `STD-000001` | `students/services.py` |
| Riwayat status | `STATUS_EVENT` (students) | `EVT-000001` | `students/services.py` |
| Orang tua | `PARENT_MASTER` (students) | `PAR-00001` | `students/services.py` |
| Catatan murid | `CatatanMurid` (students, baru) | pk | `students/services.py` |
| Kelas | `CLASS_MASTER` (classes) | `CLS-<kode>` / Kode Kelas | `classes/services.py` |
| Anggota kelas | `CLASS_MEMBERS` (classes) | `MBR-…` | `classes/services.py` |
| Jadwal resmi | `CLASS_SCHEDULE` (classes) | `SCH-…` | `classes/services.py` |
| Sesi | `SESI` (classes) | `SES-yyyymmdd-<slot>` | `classes/services.py` |
| Kehadiran | `Kehadiran` (classes, baru) | (cabang, sesi, murid) unik | `classes/services.py` |
| Guru | `TEACHER_MASTER` (masterdata) | `TCH-APP-001` | `masterdata/services.py` |
| Program / level | `PROGRAM_MASTER` (masterdata) | `PRG-…` | — |
| Akademik | `ACADEMIC_RECORD` (students) | `AKD-000001` | `students/services.py` |
| Follow-up / tugas | `FOLLOW_UP` (students) + kolom aplikasi | `FU-000001` | `students/services.py` |
| OFF | `STUDENT_OFF` (students) | `OFF-<std>-yyyymm` | `students/services.py` |
| Periode | `PERIODE` (finance) | `yyyy-mm` | `finance/services.py` |
| Tagihan SPP | `SPP_TAGIHAN` (finance) | `TAG-yyyymm-STD` | `finance/services.py` |
| Pembayaran | `BUKTI_BAYAR` (finance) | `BYR-000001` | `finance/services.py` |
| Buku kas (riwayat) | `BUKU_KAS` (finance) | ID Baris | `dashboards/calc/kas.py` |
| Notifikasi | `Notifikasi` (core, baru) | pk | `core/notifications.py` |
| Audit | `AUDIT_LOG` (audit) + `SecurityEvent` (audit, baru) | `LOG-000001` | `core/audit.py` |

## 3. Lapisan

```
views (izin, form, HTMX)  →  services (aturan, transaksi, audit)  →  models (v4 + baru)
                ↘ calc (perhitungan baca-saja, dipakai dasbor, laporan, profil, uji)
```

- `core/permissions.py` — izin bernama, `require_perm`, `perm` di template.
- `core/ui.py` — paginasi, pengurutan, filter terstandar untuk tabel.
- `templates/components/` — page header, breadcrumb, KPI, tabel data, filter, tab, modal konfirmasi, toast, empty/error state.

## 4. Urutan pembangunan

1. Fondasi: izin bernama, navigasi lengkap, komponen UI, audit masuk/keluar, notifikasi.
2. Operasional inti: Murid (daftar, profil 360°, tambah/ubah/status/kelas/catatan), Orang Tua, Kelas, Guru, Sesi & Kehadiran, Akademik.
3. Keuangan: periode (BULAN BARU / TUTUP BULAN), tagihan, pembayaran, verifikasi, tunggakan, dasbor keuangan.
4. Kecerdasan operasional: OFF, Follow-up (Action Center), notifikasi.
5. Laporan: laporan operasional, akademik, keuangan, cabang + ekspor CSV.
6. Pengerasan: keamanan, performa, izin, audit, responsif, regresi.

Detail izin: `docs/PERMISSIONS.md`.
