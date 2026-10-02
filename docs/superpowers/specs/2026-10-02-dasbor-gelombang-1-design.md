# Dasbor gelombang 1 — sistem desain B, Beranda, Laporan Murid & SPP, akun demo

Tanggal: 2 Okt 2026 · Status: disetujui per bagian (gaya B, gelombang Beranda + Laporan, OFF & Kelas dihitung untuk Beranda,
pendekatan A, bagian 1–5) · Dasar: aplikasi Excel v4 Jakarta (`..\APP\SPI_STUDENT-SPP_APP_2026_09_v4.xlsm`), spesifikasi utama
`2026-09-30-spi-web-design.md`.

## 0. Keputusan pemilik

| No | Keputusan |
|---|---|
| G1 | Akun demo & dasbor untuk dicoba sendiri di laptop; data asli Jakarta di database lokal boleh dipakai. |
| G2 | Gelombang 1 = Beranda (HOME) + Laporan Murid & SPP (DASHBOARD). Dasbor OFF, Kelas, Finance, Akademik, Marketing, Perlu Tindakan menyusul. |
| G3 | Gaya B "kartu berwarna": tiap topik punya warna & ikon. |
| G4 | Kartu OFF & Kelas di Beranda dihitung sekarang; kartu Perlu tindakan "menyusul". |
| G5 | Pendekatan A: rumus Excel disalin ke Python dan diuji terhadap angka emas yang dihitung Excel sendiri (salinan workbook, COM). |

## 1. Tujuan dan batasan

- Angka di web **sama persis** dengan Excel untuk kondisi yang sama (data, bulan/filter, tanggal "hari ini"). Tidak ada definisi baru.
- Tampilan lebih menarik dan interaktif (kartu berwarna, grafik, filter tanpa muat ulang, klik untuk menyaring) tanpa mengubah logika.
- Item yang logikanya belum dibangun tampil sebagai **menyusul** (bukan angka 0 yang bisa menyesatkan):
  kartu Perlu tindakan; Tagihan belum dibayar dan tagihan/terbayar/sisa (tahap SPP); Cuti ≥ 2 bulan dan sesi belum dikonfirmasi
  (tahap operasional); kartu "Nama menunggu" (butuh data CEK NAMA).
- Workbook di `..\APP` hanya dibaca. Alat angka emas bekerja pada salinan di folder sementara.

## 2. Sistem desain (gaya B)

**Token warna** (Tailwind `@theme`): `brand-*` tetap (menu, tombol utama). Topik, masing-masing 50 / 100 / 600 / 800:

| Topik | Ramp | 50 | 100 | 600 | 800 |
|---|---|---|---|---|---|
| murid | biru | #e6f1fb | #b5d4f4 | #185fa5 | #0c447c |
| spp | hijau | #eaf3de | #c0dd97 | #3b6d11 | #27500a |
| off | kuning | #faeeda | #fac775 | #854f0b | #633806 |
| kelas | ungu | #eeedfe | #cecbf6 | #534ab7 | #3c3489 |
| kritis | merah | #fcebeb | #f7c1c1 | #a32d2d | #791f1f |
| akad | toska | #e1f5ee | #9fe1cb | #0f6e56 | #085041 |

Status: baik #0ca30c, perhatian #fab219, serius #ec835a, kritis #d03b3b — selalu dengan ikon + teks.
Grafik kategori (urutan tetap, divalidasi buta warna): #2a78d6, #eb6834, #1baf7a, #eda100, #e87ba4, #008300, #6250d6, #e34948.

**Huruf & ikon**: Plus Jakarta Sans (npm `@fontsource/plus-jakarta-sans`, disajikan lokal), angka `tabular-nums`; Tabler Icons
(`@tabler/icons-webfont`, lokal); grafik Chart.js 4 (lokal).

**Komponen** (partial template): kartu KPI (`warna`, ikon, label, nilai, keterangan, tautan, keadaan `menyusul`), bilah filter,
kartu grafik (legenda HTML, tooltip, tombol "lihat tabel"), tabel bergulir dengan lencana status, kartu daftar perhatian, kotak cari,
judul bagian. Animasi 150–200 ms, mati bila `prefers-reduced-motion`.

**Interaksi**: filter Laporan = form GET; HTMX menukar isi dasbor (`hx-push-url`, tombol kembali bekerja); klik kartu / batang grafik
status → daftar murid tersaring (parameter `daftar`); "tampilkan semua" daftar murid; cari murid sambil mengetik (jeda 300 ms).

## 3. Lapisan perhitungan (app `dashboards`, paket `calc`)

Semua fungsi menerima `branch` dan (bila perlu) `today: date`; tampilan memakai `timezone.localdate()`, uji memakai 30 Sep 2026
(nilai `hari_ini` saat workbook disimpan). Pembulatan angka tampilan memakai pembulatan Excel (setengah menjauhi nol).

### 3.1 Daftar & periode (`LISTS`)
- Bulan riwayat = bulan berbeda di `D_BULAN` (urut), label `Mmm yyyy` Indonesia (Jan … Mei … Agu … Okt … Des), label pendek `Mmm yy`.
- Program = kata pertama tiap `Level (Grade)` di `D_BULAN`, urut Foundation, Development, Exploration, Research, lalu abjad.
- Level = semua `Level (Grade)` berbeda, urut program lalu teks. Tipe = `Tipe Kelas (rapi)` `D_MURID` berbeda (abjad).
  Mode = `Mode (rapi)` `D_MURID` berbeda (abjad). Guru = `Guru (rapi)` `D_BULAN`, urut jumlah kemunculan menurun; seri: urutan
  kemunculan pertama menurut baris sheet.
- Periode v4 = Jan 2024 … Des 2027 (`yyyy-mm`, label `Mmm yyyy`). Periode berjalan = `PERIODE` berstatus OPEN.
- Bulan buku kas = bulan berbeda di `BUKU_KAS`; terakhir & sebelumnya; tanggal terakhir = tanggal terbesar di bulan terakhir.

### 3.2 Status murid (`STUDENT_MASTER`, `C_MURID`)
- `Kelompok` `D_BULAN` = Aktif bila Status ∈ {Aktif, Baru, Rejoin}; Cuti; Off; selain itu kosong. `Program` `D_BULAN` = kata pertama Level.
- Status sekarang = status `STATUS_EVENT` terakhir (urut tanggal efektif lalu baris) dengan tanggal ≤ hari ini; bila tidak ada,
  `Status Awal (Sep 2026)`; bila kosong, PENDING.
- Kode kelas dipakai = `Kode Kelas (ubah)` bila terisi, selain itu kode terbaca (kolom sumber `kode_use` Excel).
- Status akhir periode P = event terakhir ≤ akhir P; bila tidak ada: P ≤ Sep 2026 → status `D_BULAN` bulan P dipetakan
  (Aktif/Baru/Rejoin → ACTIVE, Cuti → ON LEAVE, Off → OFF, lainnya kosong); P > Sep 2026 → `Status Awal (Sep 2026)`.

### 3.3 Laporan bulanan (`C_DASH`, `C_LIST`)
Baris = murid `D_MURID` (urutan sheet). Untuk bulan B: data bulan dari `D_BULAN` kunci `ID v1|yyyymm`. Ikut filter = punya baris
bulan B dan (program, tipe, mode, guru) baris itu cocok ("Semua" = lolos).
- Total data murid = ikut & Kelompok ∈ {Aktif, Cuti}; Aktif = Kelompok Aktif; Baru / Rejoin = Status; Cuti; Off = Kelompok Off.
- Off baru = ikut & Status Off & status bulan sebelumnya terisi dan bukan Off. Retensi = "TIDAK TERSEDIA".
- Tren (33 bulan, semua baris `D_BULAN`, filter selain bulan): Kelompok Aktif, Cuti, Off, Status Baru per bulan.
- Komposisi bulan B (ikut filter): per Status (Aktif, Baru, Rejoin, Cuti, Off); Aktif per Level; per Tipe; per Guru (10 teratas daftar
  Guru + "Lainnya / kosong" = sisa).
- Daftar perhatian: murid Baru (ikut), Off baru, Aktif belum ada pembayaran — 8 pertama + jumlah.
- Daftar murid: semua yang ikut filter (urutan `D_MURID`): nama, status, program, level, kode kelas (`D_MURID`), guru, tipe, mode,
  SPP diterima bulan B, status bayar, Student ID; 30 pertama + "tampilkan semua".

### 3.4 Buku kas (`BUKU_KAS` kolom rumus, `C_KAS`)
- Dihitung: disimpan dari impor (perbaikan impor 1A); baris Agustus 2026 dengan dua jurnal mengikuti SETTINGS `jurnal_agu`:
  versi `T ·` (tersembunyi) = YA hanya bila "Jurnal Penerimaan (tersembunyi)"; versi `R ·` = TIDAK hanya bila pilihan itu.
- Student ID 1–4 & Bagian 1–4: koreksi (`Murid (koreksi)`, `Murid kedua`) menang atas hasil sistem; "BUKAN MURID" = tanpa murid;
  dua murid koreksi = nominal dibagi dua; selain itu ID & bagian sistem.
- SPP per bulan: Total = Σ Nominal (Jenis SPP, Dihitung YA); Tertaut = Σ Bagian 1–4; Belum tertaut = Total − Tertaut.
- SPP murid bulan B = Σ bagian untuk Student ID itu (bulan ≥ Jul 2024, else 0). Status bayar: sebelum Jul 2024 "(belum ada buku kas)";
  Agustus 2026 & jurnal belum diputuskan "perlu keputusan"; > 0 "Sudah ada pembayaran"; Kelompok Aktif "Belum ada pembayaran".
- KPI: diterima bulan B; tahun ini s/d B; aktif (filter); aktif sudah bayar (n · % dibulatkan); aktif belum ada pembayaran;
  penerimaan belum tertaut (baris SPP tanpa Student ID 1 − baris koreksi BUKAN MURID; "—" sebelum Jul 2024 / Agustus belum diputuskan);
  tautan lemah = baris `Keyakinan` diawali "Lemah" tanpa koreksi (semua bulan).

### 3.5 Kelas (`CLASS_MASTER`, `C_KELAS`)
Kapasitas = SETTINGS menurut huruf pertama kode (F/P/G/S). Aktif = murid dengan kode dipakai = kode & status sekarang ACTIVE;
Cuti = ON LEAVE. Status kapasitas: 0 → KOSONG, > kapasitas → OVER CAPACITY, = → FULL, lainnya NORMAL. Status kelas: aktif > 0
ACTIVE, cuti > 0 CUTI, ada anggota di `CLASS_MEMBERS` INACTIVE, lainnya UNKNOWN. Kursi kosong = kelas ACTIVE bertipe Partner/Group
berkapasitas angka: max(kapasitas − aktif, 0). Ringkasan: kelas aktif, penuh, kursi kosong, melebihi.

### 3.6 OFF (`STUDENT_OFF` kolom rumus, `C_OFF`)
Status: event ACTIVE murid itu pada/sesudah tanggal Off (atau bulan Off) → "KEMBALI (aktif lagi · INPUT CENTER)"; selain itu status
riwayat (kosong = MASIH OFF). Lama OFF = bulan penuh dari bulan Off ke bulan ini (hanya MASIH OFF). Follow-up dari `FOLLOW_UP`
(Student ID sama, tanggal ≥ bulan Off; baris terakhir sheet): tindak lanjut, tanggal terakhir, tanggal berikutnya. Prioritas: bukan MASIH
OFF → SELESAI (kembali) / PANTAU; "Kasus ditutup" → SELESAI; berikutnya ≤ hari ini → HARI INI; tanpa tindak lanjut & tanggal follow-up
dan bulan Off ≥ bulan lalu → MENDESAK; tanpa keduanya & lama ≤ `off_lama` → MINGGU INI; lainnya PANTAU.
Ringkasan Beranda: masih off; perlu follow-up (MENDESAK + HARI INI + MINGGU INI); baru Off bulan ini.

### 3.7 Lain-lain
- Masalah kritis = `ISSUE_UNIT` severity CRITICAL, status bukan RESOLVED/CLOSED, kondisi bukan CLEARED; teks: jurnal Agustus belum
  diputuskan → "Jurnal Agustus 2026 perlu keputusan (SETTINGS)", tanpa masalah → "tidak ada masalah kritis terbuka", lainnya
  "lihat TINDAKAN bagian 0".
- Bukti bayar: menunggu verifikasi = `Status Verifikasi` "Belum Diverifikasi"; perlu klarifikasi = "Tidak Cocok" + "Perlu Klarifikasi".
- Periode operasional v4 (Laporan): status akhir periode (ACTIVE, ON LEAVE, OFF, PENDING); MASUK, OFF baru, CUTI baru, AKTIF KEMBALI
  (event periode itu); sesi REALIZED + MAKE-UP, CANCELLED; lead baru, follow-up, catatan akademik per periode.

## 4. Halaman

**Beranda** (`/`): judul cabang + periode berjalan + "riwayat DB Murid s/d … · buku kas s/d …"; Situasi sekarang 3×3 (Murid aktif ·
SPP bulan buku kas terakhir · Murid OFF / Kelas aktif · Perlu tindakan [menyusul] · Masalah kritis / Tagihan belum dibayar [menyusul] ·
Menunggu verifikasi · Cuti & sesi [menyusul]) dengan keterangan seperti Excel; Operasional bulan ini (teks periode; BULAN BARU / TUTUP
BULAN "tahap 2"); Cari murid (nama, status sekarang, kode kelas dipakai, guru dipakai, Student ID); Menu (halaman yang ada); Terakhir
diperbarui (batch impor terakhir).

**Laporan Murid & SPP** (`/laporan/`): bilah filter; kartu murid (8); kartu SPP (8, "Nama menunggu" menyusul); 7 grafik; daftar
perhatian; daftar murid; periode operasional v4 (pemilih periode sendiri, bawaan periode berjalan).

Hak akses: kemampuan VIEW (Branch Admin, Manager, CSO, Finance, Academic, Super Admin); Teacher tetap tanpa halaman. Menu: Beranda,
Laporan.

## 5. Akun demo

`DEMO_ACCOUNTS` (bawaan False) dan `DEMO_PASSWORD` di `.env`. Pemeriksaan sistem menolak `DEMO_ACCOUNTS` tanpa DEBUG. Perintah
`seed_demo_accounts` (butuh DEBUG & DEMO_ACCOUNTS; membuat kata sandi acak ke `.env` bila kosong) membuat/memperbarui akun aktif:
super admin; SPI Jakarta: Branch Admin, Manager, CSO, Finance, Academic, Teacher (nama guru = baris pertama `TEACHER_MASTER`);
SPI Alam Sutera: Branch Admin. Email `peran.cabang@spi.local`. Panel "Akun demo" di halaman Masuk (hanya bila `DEMO_ACCOUNTS`):
klik → isi & kirim. Daftar akun di `docs/AKUN_DEMO.md` (tanpa kata sandi).

## 6. Pengujian

- **Angka emas**: `tools/export_golden.py` (Python sistem + pywin32) menyalin workbook Jakarta ke folder sementara, membuka di Excel
  tanpa makro, mengunci `hari_ini` = 30 Sep 2026, lalu untuk tiap skenario (bulan / program / tipe / mode / guru; periode v4) menghitung
  ulang dan membaca: KPI & teks HOME/DASHBOARD, tabel grafik `C_DASH`/`C_KAS`, baris per murid (`C_DASH`, `C_KAS`, `STUDENT_MASTER`),
  `STUDENT_OFF`, `CLASS_MASTER`, `LISTS`. Hasil JSON di `dashboards/tests/golden/` (Student ID & angka, tanpa nama/kontak).
- Uji lambat: impor workbook Jakarta → setiap angka & baris = JSON, tanpa toleransi.
- Uji cepat: aturan-aturan di bagian 3 dengan data kecil; tampilan (200 untuk peran VIEW, 403 Teacher, cabang lain tidak bocor,
  respons HTMX parsial, parameter filter tidak sah → bawaan); akun demo (perintah idempoten, ditolak tanpa flag, panel tersembunyi);
  tata letak (tabel bergulir).
- Browser: desktop & 375 px, tanpa error konsol; angka Beranda/Laporan = Excel.
