# Spesifikasi Desain — SPI Management Web Application

- **Tanggal:** 30 September 2026
- **Status:** disetujui per bagian dalam percakapan; menunggu tinjauan dokumen ini
- **Lokasi aplikasi:** `C:\Users\SPI Workshop\Downloads\management excel\app web`
- **Acuan fungsional:** `C:\Users\SPI Workshop\Downloads\management excel\APP` —
  `SPI_STUDENT-SPP_APP_2026_09_v4.xlsm` (Jakarta), `SPI_ALAM_SUTERA_v4.xlsm`, `SPI_BRANCH_TEMPLATE_v4.xlsm`

## 0. Keputusan yang sudah diambil

| # | Pertanyaan | Keputusan |
|---|---|---|
| D1 | Di mana aplikasi berjalan | **Server internet / cloud** — semua cabang lewat browser. PostgreSQL, email lewat SMTP. Selama pengembangan berjalan di komputer ini. |
| D2 | Pencatatan uang masuk (buku kas) | **Tetap dari Excel, diunggah ke web** (Laporan Admin bulanan) dengan logika penautan yang sama dengan pipeline. BUKU_KAS tetap satu-satunya sumber resmi uang masuk (K1). |
| D3 | Pendekatan teknis | **Django full-stack** (Python) + PostgreSQL + Tailwind / HTMX / Alpine.js / Chart.js. |
| D4 | Invoice / receipt | **Nota** (satu dokumen, satu seri nomor, seperti Excel) — tidak ada seri nomor kuitansi kedua. |
| D5 | Keputusan pemilik yang tetap berlaku | K1 hibrida (BUKU_KAS otoritatif), K2 kontak disimpan tetapi **tidak pernah ikut CSV**, K3 tarif fee guru **tidak dikarang** ("Tarif belum tersedia"), K4 tagihan menurut status & periode. |

## 1. Tujuan dan kriteria berhasil

Web app adalah **versi web dari sistem Excel SPI v4 yang sudah ada** — bukan sistem baru. Struktur data, alur kerja, logika bisnis,
perhitungan, otomasi, penomoran ID, jejak audit dan relasi sumber-kebenaran sama dengan Excel; tampilannya aplikasi SaaS modern
(bukan tampilan spreadsheet), berbahasa Indonesia seperti Excel.

Berhasil bila:
1. Semua fungsi 18 halaman v4 dan fungsi sheet admin tersedia di web (bagian 4).
2. Semua otomasi VBA punya aksi web dengan perilaku sama (bagian 6).
3. Data Jakarta termigrasi utuh (ID, riwayat, keuangan, status, relasi) dan **angka web = angka Excel tanpa toleransi** untuk daftar
   uji di bagian 8; skenario uji Excel (v4_test 67 pemeriksaan, branch_test 90 pemeriksaan) memberi hasil yang sama di web.
4. Cabang terisolasi: pengguna hanya melihat & mengubah data cabang yang diizinkan; cabang baru dimulai kosong dari konfigurasi template.
5. Login aman: hash password, sesi, verifikasi email, reset password, akses menurut peran & cabang.

Di luar lingkup: fitur yang tidak ada di Excel (kecuali halaman autentikasi & manajemen pengguna yang diminta spesifikasi), sinkronisasi
dua arah dengan Excel, pencatatan kas langsung di web (lihat D2), otomasi terjadwal yang tidak ada di Excel.

## 2. Sumber acuan (spesifikasi perilaku)

Rumus Excel dan kode VBA dibangkitkan oleh pipeline Python di `management excel\00_SYSTEM\APP_BUILD_V2\_scripts`. Kode itu adalah
**spesifikasi perilaku** yang dipindahkan ke web; bila ragu, perilaku file Excel v4 yang menentukan.

| Perilaku | File acuan |
|---|---|
| Definisi 33 tabel (kolom, kunci, jenis kolom, format) | `v2_layout.py` (`TABLES`, `APP_TABLES`) |
| Kolom rumus tabel master & anggota kelas, SETTINGS, AUDIT diff | `v2_build_sheets.py` |
| Tabel v4 (PERIODE, STATUS_EVENT, PARENT, SPP_TAGIHAN, BUKTI_BAYAR, SESI, TARIF_FEE, FOLLOW_UP, ACADEMIC_RECORD, LEAD, DOKUMEN, BUKU_KAS_KELUAR) + mesin status C_MURID | `v4_build_sheets.py` |
| BUKU_KAS, PEMBAYAR, NOTA_LOG, C_KAS | `v3_build_sheets.py`, `v3_kas.py` |
| Dashboard OFF / KELAS, PERLU_TINDAKAN, pemeriksaan V4 | `v2_dash.py` |
| INPUT CENTER (12 form + pemeriksaan), FINANCE, TEACHER_FEE, MARKETING, LAPORAN v4, DATA_QUALITY v4 | `v4_pages.py` |
| HOME, MURID, MATRIKS, PROFIL_MURID, SPP, NOTA, AKADEMIK, SIMULASI | `app_build.py`, `app_build_views*.py`, `v3_pages.py` |
| Otomasi (form, BULAN BARU, TUTUP BULAN, verifikasi) | `v4_vba.py` (modul `InputCenter`, `Periode`) |
| Ekspor PDF / CSV, Buat Nota, klik 2×, isian profil, audit | `v2_vba_modules.py` (modul `Ekspor`, `Aplikasi`) |
| Impor buku kas (Jurnal Penerimaan = Arus Kas, penautan nama, bagi bayar keluarga, periode tagihan) | `v3_extract.py`, `v3_model.py`, `v3_names.py` |
| Pengeluaran & kontak | `v4_extract.py`, `v4_model.py` |
| Konfigurasi SPI untuk cabang baru | `_branches\system_config.json`, `branch_model.py` |
| Uji skenario yang harus direplikasi | `v4_test.py`, `branch_test.py` |

## 3. Arsitektur

### 3.1 Proyek dan modul
Satu proyek Django `spi_web` (repositori git di `app web`). Modul (Django app) mengikuti domain Excel:

| Modul | Tabel / fungsi |
|---|---|
| `accounts` | pengguna (login email), peran per cabang, daftar / verifikasi email / lupa & reset password, persetujuan akses |
| `branches` | cabang (identitas SETTINGS), parameter SETTINGS per cabang, pembuatan cabang baru dari konfigurasi template |
| `masterdata` | PROGRAM_MASTER, OFF_REASON_MASTER, TARIF_FEE, UNIT_MASTER, TEACHER_MASTER, ROOM_MASTER, PARTNER_MASTER, daftar pilihan |
| `students` | STUDENT_MASTER, PARENT_MASTER, STATUS_EVENT, STUDENT_OFF, FOLLOW_UP, ACADEMIC_RECORD, DOKUMEN, LEAD, STUDENT_ID_MAPPING, riwayat bulanan DB Murid |
| `classes` | CLASS_MASTER, CLASS_MEMBERS, CLASS_SCHEDULE, SESI, SIMULASI_JADWAL |
| `finance` | PERIODE, SPP_TAGIHAN, BUKTI_BAYAR, BUKU_KAS, BUKU_KAS_KELUAR, PEMBAYAR, NOTA_LOG, data pembanding SPP lama |
| `quality` | ISSUE_UNIT, keputusan CEK_NAMA, pemeriksaan DATA_QUALITY |
| `audit` | AUDIT_LOG, IMPORT_LOG, SOURCE_REFERENCE |
| `importer` | migrasi workbook v4, unggah buku kas bulanan |
| `reports` | HOME, dashboard, PERLU_TINDAKAN, FINANCE, MARKETING, TEACHER_FEE, AKADEMIK, MATRIKS, LAPORAN |

### 3.2 Lapisan
- **Model (tabel):** hanya menyimpan yang di Excel memang disimpan (bagian 5).
- **Service:** semua perhitungan (padanan kolom rumus & sheet C_*) dan semua aksi (padanan VBA). Satu fungsi dipakai semua halaman
  ("satu input → semua halaman ikut").
- **View & template:** halaman dan form memanggil service; tidak ada logika bisnis di template.
- Perhitungan berat (dashboard) boleh di-cache per cabang & periode, dibatalkan setiap ada penulisan pada cabang itu.

### 3.3 Teknologi
Django 5.x, PostgreSQL 16, Argon2 (hash password), Tailwind CSS, HTMX, Alpine.js, Chart.js, xhtml2pdf (nota & PDF halaman dari
template HTML, Python murni), openpyxl (impor Excel). Pengembangan & uji memakai PostgreSQL lokal (versi portabel di komputer ini) —
tidak memakai SQLite agar perilaku sama dengan server.

Zona waktu **Asia/Jakarta**. "Hari ini" (jatuh tempo, Terlambat, lama cuti / OFF, follow-up jatuh tempo) = tanggal hari ini di
Asia/Jakarta, sama dengan `set_HariIni = TODAY()` di Excel; hanya uji otomatis yang boleh menggantinya. Nominal dalam Rupiah bulat.

### 3.4 Isolasi cabang
- Setiap baris operasional punya `branch` (wajib). Kunci bisnis unik per cabang: (branch, Student ID), (branch, Nomor Nota), dst.
- "Cabang aktif" per sesi; pengguna hanya bisa memilih cabang tempat ia punya peran; SUPER_ADMIN bisa memilih semua.
- Penyaringan dipaksa terpusat (manajer query berbasis cabang + middleware + pemeriksaan di setiap service), bukan di tiap halaman.

### 3.5 ID dan penomoran
Format sama dengan Excel: `STD-000001`, `PAR-00001`, `EVT-000001`, `TAG-<yyyymm>-<Student ID>`, `BYR-000001`, `SES-<yyyymmdd>-<slot>`,
`SES-<yyyymmdd>-MU-01`, `SES-<yyyymmdd>-PD-01`, `SCH-APP-001`, `TCH-APP-001`, `CLS-<kode>`, `FU-000001`, `AKD-000001`, `LEAD-00001`,
`DOK-000001`, `LOG-000001`, nota `<awalan><tahun>/<urut 4 digit>`. Aturan `IdBaru`: nomor berikutnya setelah nomor tertinggi dengan awalan
itu di cabang itu; nomor tidak pernah dipakai ulang. Dibuat dalam transaksi database dengan penguncian agar dua pengguna tidak mendapat
nomor yang sama.

## 4. Halaman dan alur kerja

| Menu | Halaman web | Asal Excel |
|---|---|---|
| Beranda | HOME: KPI, cari murid, tombol BULAN BARU / TUTUP BULAN, pintasan | HOME |
| Input | Pusat Input: 12 form (lampiran A) dengan field, pemeriksaan "Lengkapi / ⚠ / ✓" dan konfirmasi yang sama; form yang sama dibuka dari konteks (mis. "Murid Baru" di MURID, "Catat Pembayaran" di profil) | INPUT CENTER |
| Murid | Daftar murid per periode + filter status · Profil 360° bertab: identitas & orang tua, status & cuti, kelas & jadwal, SPP (tagihan, bukti, buku kas, nota), akademik, OFF & follow-up, dokumen, sesi, issue, riwayat audit | MURID, PROFIL_MURID |
| Keuangan | SPP (buku kas per bulan & kontrol) · Finance (tagihan, verifikasi bukti, PERLU DICEK, pengeluaran / royalti / setor pusat) · Nota (buat nota PDF, NOTA_LOG) · Unggah Buku Kas | SPP, FINANCE, NOTA, impor pipeline |
| Kelas | Dashboard Kelas · Jadwal Resmi · Simulasi Jadwal · Teacher Fee | DASHBOARD_KELAS, CLASS_SCHEDULE, SIMULASI_JADWAL, TEACHER_FEE |
| OFF | Dashboard OFF (alasan, lama OFF, follow-up, aktif kembali) | DASHBOARD_OFF |
| Akademik | progres, Student Report, sertifikat, rekomendasi | AKADEMIK |
| Marketing | lead → contacted → trial → registered → active / off-lost | MARKETING |
| Perlu Tindakan | prioritas mendesak / hari ini / minggu ini / pantau | PERLU_TINDAKAN |
| Laporan | laporan murid & SPP bulanan + blok periode operasional v4 · Matriks riwayat status | DASHBOARD (LAPORAN), MATRIKS |
| Admin | Data Quality · Master Data (kelas, anggota kelas, alasan OFF, unit, issue, pemetaan ID, CEK NAMA, pembanding SPP lama: SPP_TERPADU / CEK_SPP / ISI_SPP) · Guru · Program · Partner · Ruang · Audit Log · Settings (identitas cabang, parameter, tarif fee) · Impor Data · Pengguna & Cabang · Panduan | sheet admin, SETTINGS, PANDUAN |
| Autentikasi | LOGIN, DAFTAR, VERIFIKASI EMAIL, LUPA PASSWORD, RESET PASSWORD | (baru, sesuai spesifikasi) |

Padanan interaksi: sel kuning → edit di tabel admin (langsung tercatat di Audit Log); sel kuning FINANCE → tombol Verifikasi;
isian PROFIL → catatan baru (riwayat tidak ditimpa); klik 2× nama → tautan profil; pemilih periode / filter → filter web yang diingat per
pengguna; tombol PDF / CSV → ekspor per halaman (CSV UTF-8 tanpa kolom kontak, K2).

## 5. Model data

### 5.1 Aturan pemetaan kolom (jenis kolom dari `v2_layout.py`)
- ASLI, SEBAGIAN, SISTEM, TURUNAN, KOSONG, INPUT → **disimpan**.
- FORMULA → **tidak disimpan**, dihitung di service dengan hasil sama dengan rumus Excel.
- Kolom asal-usul (Source File / Sheet / Row / Type, Import Batch, Import Date) dan validasi (Validation Status, Validator, Validation
  Date, Catatan Validator) → disimpan.
- Kolom "(ubah)" STUDENT_MASTER (kode kelas, program, level, guru, harga, sekolah) → disimpan; nilai "dipakai" = ubahan bila ada,
  selain itu nilai sumber.

### 5.2 Tabel
- 33 tabel v4 dengan `branch`: STUDENT_MASTER, STUDENT_ID_MAPPING, STUDENT_OFF, OFF_REASON_MASTER, CLASS_MASTER, CLASS_MEMBERS,
  CLASS_SCHEDULE, TEACHER_MASTER, PROGRAM_MASTER, PARTNER_MASTER, ROOM_MASTER, UNIT_MASTER, ISSUE_UNIT, BUKU_KAS, PEMBAYAR, NOTA_LOG,
  SIMULASI_JADWAL, PERIODE, STATUS_EVENT, PARENT_MASTER, SPP_TAGIHAN, BUKTI_BAYAR, SESI, TARIF_FEE, FOLLOW_UP, ACADEMIC_RECORD, LEAD,
  DOKUMEN, BUKU_KAS_KELUAR, SETTINGS, IMPORT_LOG, SOURCE_REFERENCE, AUDIT_LOG (672 kolom di Excel).
- Riwayat bulanan DB Murid (Jakarta Jan 2024 – Sep 2026; 5.488 baris murid-bulan) — dasar status s/d Sep 2026, MATRIKS, laporan bulanan v1.
- Data pembanding SPP lama (SPP Controling, SPP di DB Murid, keputusan CEK_NAMA) — hanya untuk halaman pembanding.
- Pengguna, cabang, keanggotaan (pengguna × cabang × peran).
- Tidak ada entitas lain.

### 5.3 Relasi (mengikuti Excel)
- Kunci bisnis Excel dipertahankan (bagian 3.5) + kunci internal database.
- Murid ↔ kelas lewat **kode kelas** (teks), murid ↔ guru lewat **nama guru**, sama seperti Excel (peringatan "kode kelas belum ada di
  CLASS_MASTER" tetap berfungsi). Tagihan, sesi, event status, bukti bayar, follow-up, akademik, dokumen, Off → murid lewat Student ID;
  murid → orang tua lewat Parent ID; sesi → slot lewat Schedule ID.

### 5.4 Tidak menjadi tabel
Sheet kalkulasi C_* dan mesin C_MURID (→ service); LISTS (→ pilihan di kode untuk nilai tetap, query untuk guru / kode kelas / periode);
DATA_DICTIONARY (→ dibangkitkan dari definisi model); tata letak halaman (→ template).

## 6. Perhitungan dan otomasi

### 6.1 Otomasi VBA → aksi web

| Excel | Aksi web (perilaku sama) |
|---|---|
| `InputCenter.Simpan <form>` (12 form) | simpan per form dengan pemeriksaan & konfirmasi yang sama, menulis ke tabel yang sama (lampiran A) |
| `IdBaru` | bagian 3.5 |
| `Periode.BulanBaru` | periode berikutnya OPEN (periode pertama cabang = bulan buka dari SETTINGS); tagihan `TAG-yyyymm-STD` untuk murid ACTIVE pada hari pertama periode yang punya harga dan belum ditagih; sesi dari slot jadwal yang berlaku; periode lama → CLOSING; tidak pernah dobel |
| `Periode.TutupBulan` | CLOSING → CLOSED dengan ringkasan (sesi belum dikonfirmasi, bukti belum diverifikasi, belum dibayar, perlu klarifikasi); input ke periode CLOSED ditolak |
| verifikasi di FINANCE (`Workbook_SheetChange`) | Verified / Tidak Cocok / Perlu Klarifikasi + oleh / pada + audit |
| Buat Nota (`Aplikasi`) | nomor berikutnya per tahun, PDF, baris NOTA_LOG; nomor tidak pernah dipakai ulang |
| isian PROFIL (`Aplikasi.ProfilUbah`) | catatan baru di ACADEMIC_RECORD / FOLLOW_UP + audit |
| `Ekspor` PDF / CSV, klik 2× | ekspor per halaman (CSV tanpa kontak), tautan profil |
| `CatatAudit` | AUDIT_LOG `LOG-000001`: pengguna, aksi, entitas, ID, kolom, nilai lama, nilai baru, waktu, "APLIKASI" |
| impor buku kas (pipeline) | unggah buku kas bulanan (bagian 7.4) |

### 6.2 Rumus → service (hasil harus sama dengan Excel)
- Mesin status per periode (C_MURID): perubahan terakhir di STATUS_EVENT s/d akhir periode; bila tidak ada → riwayat DB Murid
  (≤ Sep 2026: Aktif / Baru / Rejoin = ACTIVE, Cuti = ON LEAVE, Off = OFF); bila tidak ada → status awal; bila tidak ada → PENDING.
- SPP_TAGIHAN: tagihan, terbayar buku kas (per periode tagihan), terbayar bukti Verified, sisa, status (Belum Jatuh Tempo / Belum Dibayar /
  Menunggu Verifikasi / Sudah Dibayar / Perlu Klarifikasi / Terlambat), keputusan (Dibatalkan / Dibebaskan / Ditunda), pemeriksaan.
- BUKU_KAS: tautan murid, bagian per murid (bayar keluarga), periode tagihan (+ koreksi manusia), dihitung / tidak.
- CLASS_MASTER: kapasitas per tipe (SETTINGS), murid aktif / cuti / tidak aktif, utilisasi, status kapasitas, status kelas, anggota.
- TEACHER_MASTER: murid aktif, slot jadwal. SESI: kunci tarif, fee (hanya dengan tarif resmi), status konfirmasi.
- STUDENT_MASTER: kolom "dipakai", status sekarang, orang tua, kelengkapan, akademik terakhir; STUDENT_OFF: status Off, lama Off,
  follow-up terakhir, prioritas.
- 18 pemeriksaan PERLU DICEK (lampiran B), pemeriksaan tiap form, semua KPI halaman.

## 7. Migrasi dan impor

### 7.1 Jakarta
Sumber: `APP\SPI_STUDENT-SPP_APP_2026_09_v4.xlsm` apa adanya saat migrasi (termasuk catatan yang sempat dibuat di INPUT CENTER Excel).
Dibaca per tabel lewat judul kolom (definisi `v2_layout.py`): 33 tabel, riwayat bulanan DB Murid (D_BULAN), data pembanding SPP lama
(D_SPPC, D_SPPDBM, keputusan CEK_NAMA), identitas & parameter SETTINGS, riwayat AUDIT_LOG / IMPORT_LOG / NOTA_LOG. Hanya nilai
tersimpan yang diimpor; nilai rumus Excel di file dipakai sebagai pembanding (bagian 8).

### 7.2 Alur impor
1. Pilih file → baca → validasi: kolom wajib, format ID, tipe tanggal / angka, referensi (Parent ID / Student ID / kode kelas yang dirujuk
   ada), duplikat (ID ganda = error; nama + tanggal lahir sama = peringatan).
2. **Pratinjau**: jumlah baris per tabel, daftar error & peringatan. Belum ada yang disimpan.
3. Simpan: satu transaksi (semua atau tidak sama sekali); IMPORT_LOG (batch, hash file) + AUDIT_LOG.
4. Uji coba boleh diulang; impor ke cabang yang sudah berisi data wajib konfirmasi eksplisit (tidak ada impor ganda).

### 7.3 Alam Sutera dan cabang baru
- Alam Sutera: impor `SPI_ALAM_SUTERA_v4.xlsm` — identitas & konfigurasi, tanpa data operasional.
- Cabang baru (SUPER_ADMIN): isi 8 kolom identitas (Branch ID, nama, kota, alamat, status, bahasa, mata uang, tanggal buka); konfigurasi
  SPI (16 program & level, 17 kategori OFF, kunci tarif, daftar pilihan, kapasitas per tipe) disalin dari template; tabel operasional kosong
  — setara `SPI_BRANCH_TEMPLATE_v4.xlsm`. Unit ID = `UNIT-` + Branch ID tanpa "SPI-".

### 7.4 Unggah buku kas bulanan
File "Admin <bulan> - Unit SPI <cabang>": Jurnal Penerimaan dibaca dan dicek = Arus Kas per kode (selisih = error, file ditolak); baris
ditautkan ke murid (nama pembayar / murid, bagi bayar keluarga), periode tagihan dari keterangan. Pratinjau (baris, tertaut, belum
tertaut) → simpan. Unggah ulang bulan yang sama mengganti baris bulan itu tetapi koreksi manusia (periode tagihan, tautan murid) tetap dibawa
per ID baris, seperti carry-over pipeline.

## 8. Validasi dan pengujian

### 8.1 Kesamaan dengan Excel (tanpa toleransi)
File v4 Jakarta diimpor ke database uji; nilai yang dihitung web dibandingkan dengan nilai rumus tersimpan di file yang sama:
jumlah murid per status (HOME, MURID per periode) dan status tiap murid per periode; total SPP per bulan (= Arus Kas) dan SPP per murid;
kelas (murid aktif, kapasitas, status, anggota); OFF (jumlah, daftar); 18 pemeriksaan PERLU DICEK; DATA_QUALITY; kartu FINANCE;
laporan bulanan setiap bulan; relasi Student ID. Skenario uji Excel `v4_test.py` dan `branch_test.py` diputar ulang di web dengan input
yang sama → ID, tagihan, status, nomor nota, sesi dan audit sama. Selisih apa pun dilaporkan, tidak disembunyikan.

### 8.2 Uji lain
Uji unit tiap service; uji hak akses (peran × aksi, bagian 9); uji isolasi cabang (termasuk URL / ID tebakan); uji autentikasi
(verifikasi email, reset, sesi, pembatasan percobaan login); uji impor (error, duplikat, pratinjau tanpa penyimpanan, transaksi).

## 9. Peran dan hak akses

| Kemampuan | SUPER ADMIN | BRANCH ADMIN | MANAGER | CSO | FINANCE | ACADEMIC | TEACHER |
|---|---|---|---|---|---|---|---|
| Semua cabang, buat cabang, pengguna semua cabang, konfigurasi SPI | ✓ | – | – | – | – | – | – |
| Pengguna & SETTINGS cabang, impor migrasi | ✓ | ✓ | – | – | – | – | – |
| Lihat semua halaman & laporan cabang, ekspor | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| Murid Baru / Update Murid / Lead / Follow-up / Dokumen | ✓ | ✓ | ✓ | ✓ | – | Dokumen | – |
| Perubahan Status (cuti / OFF / aktif kembali) | ✓ | ✓ | ✓ | ✓ | – | – | – |
| Bukti bayar (PB) | ✓ | ✓ | – | ✓ | ✓ | – | – |
| Verifikasi pembayaran, keputusan tagihan, koreksi periode buku kas, unggah buku kas, nota | ✓ | ✓ | – | – | ✓ | – | – |
| BULAN BARU | ✓ | ✓ | ✓ | – | ✓ | – | – |
| TUTUP BULAN | ✓ | ✓ | ✓ | – | – | – | – |
| Guru & Kelas Baru, Jadwal, Simulasi | ✓ | ✓ | ✓ | ✓ | – | ✓ | – |
| Akademik | ✓ | ✓ | ✓ | – | – | ✓ | – |
| Realisasi pertemuan / kegiatan guru | ✓ | ✓ | ✓ | ✓ | – | ✓ | sesi miliknya |
| Lihat kontak orang tua / murid | ✓ | ✓ | ✓ | ✓ | ✓ | – | – |
| Validasi data (Data Quality, CEK NAMA, issue) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |

TEACHER hanya melihat jadwal, kelas dan daftar murid kelasnya (tanpa keuangan & kontak) dan mencatat realisasi sesi miliknya.
DAFTAR membuat akun **tanpa akses**; setelah email terverifikasi, BRANCH ADMIN / SUPER ADMIN memberi cabang & peran. Satu orang boleh
punya peran berbeda di cabang berbeda. Setiap aksi dicek di server (peran + cabang); setiap perubahan tercatat di Audit Log.

## 10. Deploy dan operasi
- Paket Docker (aplikasi Django + gunicorn + file statis) dengan PostgreSQL; dapat dipasang di VPS / cloud mana pun.
- Konfigurasi lewat variabel lingkungan: kunci rahasia, URL database, SMTP (verifikasi & reset password), domain, HTTPS.
- Backup database harian (dump PostgreSQL) + prosedur pemulihan tertulis.
- Pemasangan ke penyedia cloud dilakukan bersama pemilik di akhir (butuh akun pemilik).

## 11. Tahapan pembangunan
Setiap tahap: rencana implementasi → bangun → uji → laporan ke pemilik.

| Tahap | Isi | Selesai bila |
|---|---|---|
| 1. Fondasi | proyek & PostgreSQL lokal, autentikasi lengkap, cabang & peran & isolasi, semua tabel, audit, impor (Jakarta, Alam Sutera, cabang baru), halaman HOME / MURID / PROFIL | impor Jakarta tanpa error dengan jumlah baris sama; HOME / MURID / PROFIL = Excel untuk semua murid; uji autentikasi, hak akses & isolasi lulus |
| 2. Operasional harian | 12 form, BULAN BARU / TUTUP BULAN, tagihan – verifikasi – nota, unggah buku kas, OFF & follow-up, akademik, kelas – jadwal – simulasi | skenario v4_test & branch_test di web = hasil Excel; unggah ulang 27 buku kas Jakarta menghasilkan BUKU_KAS = Excel |
| 3. Manajemen & admin | semua dashboard & laporan, FINANCE, TEACHER_FEE, MARKETING, DATA_QUALITY, CEK NAMA & pembanding SPP, settings, pengguna, ekspor PDF / CSV, panduan, paket deploy | laporan kesamaan lengkap (bagian 8.1) tanpa selisih; paket deploy teruji |

## Lampiran A — 12 form Pusat Input (sama dengan INPUT CENTER v4)

| Kode | Form | Menulis ke |
|---|---|---|
| MB | Murid Baru | STUDENT_MASTER, PARENT_MASTER, STATUS_EVENT (MASUK), SPP_TAGIHAN (bila ACTIVE dan periode berjalan ada), BUKTI_BAYAR, DOKUMEN, LEAD |
| UM | Update Murid Lama | STUDENT_MASTER kolom "(ubah)" / kontak / Parent ID, PARENT_MASTER, AUDIT_LOG |
| PB | Pembayaran (bukti bayar) | BUKTI_BAYAR (Belum Diverifikasi) |
| FU | Follow Up Orang Tua | FOLLOW_UP |
| AK | Akademik | ACADEMIC_RECORD (+ DOKUMEN bila ada link) |
| KG | Kehadiran / Kegiatan Guru | SESI (MAKE-UP) |
| RP | Realisasi Pertemuan | SESI (status, hadir / tidak hadir, guru pengganti) |
| JD | Jadwal (jadwal resmi) | CLASS_SCHEDULE (slot baru / berakhir), SESI (pindah pertemuan) |
| LD | Marketing / Lead | LEAD |
| DK | Dokumen | DOKUMEN (+ ACADEMIC_RECORD untuk Student Report / Sertifikat) |
| PS | Perubahan Status | STATUS_EVENT, STUDENT_OFF (bila OFF), tagihan periode berjalan dibuat / dibatalkan setelah konfirmasi |
| GK | Guru & Kelas Baru | TEACHER_MASTER (TCH-APP-###) atau CLASS_MASTER (CLS-<kode>) |

## Lampiran B — 18 pemeriksaan PERLU DICEK (sama dengan v4)
`tag_telat` tagihan terlambat · `tag_belum` tagihan periode berjalan belum dibayar · `bukti_belum` bukti belum diverifikasi · `bukti_cek`
bukti tidak cocok / perlu klarifikasi · `tag_klarif` tagihan perlu klarifikasi · `tag_beda` pembayaran untuk periode berbeda ·
`aktif_tanpa_tag` murid ACTIVE tanpa tagihan periode berjalan · `aktif_tanpa_harga` murid ACTIVE tanpa harga SPP · `cuti_lama` cuti ≥ 2 bulan ·
`cuti_konf` cuti belum dikonfirmasi · `pending` murid PENDING · `sesi_belum` pertemuan belum dikonfirmasi · `ganda` kemungkinan bayar ganda ·
`fu_jatuh` follow-up jatuh tempo · `lead_fu` lead tanpa perkembangan > 7 hari · `kode_baru` kode kelas tidak ada di CLASS_MASTER ·
`periode_kabur` penerimaan menyebut beberapa bulan · `status_konflik` tagihan ada tetapi murid tidak ACTIVE.
