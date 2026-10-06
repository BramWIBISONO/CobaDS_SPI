# Management layer (Management Center & halaman manajemen)

Lapisan manajemen di atas modul operasional - **hanya membaca** data yang sama (kecuali penerbitan Nota SPP), dengan
cabang & izin dicek di server. Kode: `management/services/*` (mesin hitung), `management/views*.py`, `templates/management/`.

| Halaman | URL | Izin | Untuk |
|---|---|---|---|
| Management Center | `/manajemen/` | `management.view` (Branch Admin, Manager) | Kesehatan SPI, yang perlu perhatian, perbandingan cabang (Super Admin) |
| Business Health | `/manajemen/kesehatan-bisnis/` | `management.view` | Skor + komponennya, perbandingan bulan lalu / 3 / 6 / 12 bulan, tren |
| Student Lifecycle | `/manajemen/siklus-murid/` | `management.view` | Matriks status bulanan (= sheet MATRIKS), wawasan murid, ekspor |
| Finance Control | `/manajemen/keuangan/` | `management.finance` (Branch Admin, Manager, Finance) | Tagihan, diterima, sisa, collection, risiko murid, per program / cabang |
| Nota SPP | `/manajemen/nota/` | lihat: `management.finance`; terbitkan: `nota.issue` (Branch Admin, Finance) | Nota digital A4, nomor seri, NOTA_LOG, WhatsApp |
| Operational Health | `/manajemen/operasional/` | `management.view` | Sesi, absensi, kapasitas kelas, beban guru, follow-up |
| Data Health | `/manajemen/kesehatan-data/` | `management.view` | 22 cek kelengkapan & kerapian, tiap temuan bisa dibuka |
| Management Reports | `/manajemen/laporan/` | `management.view` | Laporan Bulanan (cetak/PDF), ekspor Excel/CSV (tercatat di Audit Log) |

Super Admin = pemilik (owner): semua cabang + tabel "Cabang mana yang sehat". Tidak ada peran Owner terpisah.

## Sumber & rumus

**Murid (Student Lifecycle)** - lihat `docs/MANAGEMENT_LIFECYCLE.md`. Divalidasi sel-per-sel dengan MATRIKS Excel (323 baris formula, 0 beda).
Definisi eksplisit (DB Murid tidak punya rumus retensi): Retensi = basis bulan lalu (A/B/R/C) yang bulan ini masih A/B/R/C ÷ basis;
Churn = basis yang bulan ini O ÷ basis (= Off baru Laporan Murid); Hilang dari catatan = basis yang bulan ini ?/–/· (masalah data);
Reaktivasi = R ÷ pool Off bulan lalu; Konversi baru → aktif = B bulan lalu yang masih A/B/R/C ÷ B bulan lalu.

**Keuangan (Finance Control & Nota)** = rumus sheet NOTA (`v3_pages.py` Z1-Z14) dan SPP_TAGIHAN (`v4_build_sheets.py`):
- Diterima = bagian murid di baris BUKU_KAS jenis SPP, Dihitung = YA, **periode tagihan** = `Periode Tagihan (koreksi)` bila diisi, selain itu `(sistem)`.
- Periode sebelum `mulai_v4` (Okt 2026): tagihan = Harga SPP dipakai (harga ubah, lalu harga) → LUNAS / SEBAGIAN / BELUM TERCATAT / HARGA BELUM TERCATAT.
  Di Finance Control ini diberi label **"estimasi tagihan"** karena belum ada baris tagihan resmi.
- Periode ≥ `mulai_v4`: tagihan = SPP_TAGIHAN (harga − diskon + penyesuaian), status Sudah Dibayar / Menunggu Verifikasi / Perlu Klarifikasi /
  Pembayaran Periode Berbeda / Belum Jatuh Tempo / Terlambat / Belum Dibayar. Tanpa baris tagihan = TIDAK ADA TAGIHAN (bukan Rp 0).
- Agustus 2026 & `jurnal_agu = BELUM DIPUTUSKAN` = PERLU KEPUTUSAN (nota tidak bisa dibuat).
- Collection = Σ min(diterima, tagihan) ÷ Σ tagihan murid aktif (A/B/R) periode itu. Sisa = Σ max(0, tagihan − diterima).
- Nomor nota = `nota_awalan` + tahun + `/` + 4 digit, berurutan, tidak pernah dipakai ulang (`core.ids.next_id`); tersimpan di NOTA_LOG + Audit Log.
- Halaman menulis **mengapa angka belum lengkap** (buku kas tercatat s/d tanggal X; uang Agustus 2026 belum dihitung selama jurnal belum diputuskan).

**Operasional**: SESI (REALIZED / MAKE-UP = terlaksana), KEHADIRAN, kapasitas kelas = `calc.kelas` (pengaturan F/P/G/S), beban guru = `masterdata.services.teacher_rows`,
follow-up = `students.services.is_open_followup` / `due_bucket`.

**Data Health**: 22 cek (murid, orang tua, kelas, guru, jadwal, keuangan, riwayat status, isu). Skor = rata-rata tertimbang (1 − terkena ÷ diperiksa),
bobot kritis 3 · tinggi 2 · sedang 1,5 · rendah 1; cek tanpa data tidak dihitung.

## Skor kesehatan (usulan - perlu disahkan manajemen)

Setiap komponen: angka nyata → 0-100 secara linear antara ambang **buruk** (0) dan **baik** (100); komponen tanpa data **tidak dihitung** (bukan 0).
Skor dimensi = rata-rata komponennya; Business Health = Student 30% · Financial 30% · Operational 20% · Data 20%.
Status: Sehat ≥ 80 · Pantau ≥ 65 · Berisiko ≥ 50 · Kritis < 50. Semua ambang ada di `management/services/health.py` (`AMBANG`) dan
ditampilkan di halaman Business Health. **Ambang & bobot ini usulan awal, bukan rumus Excel** - ubah di satu tempat itu bila manajemen menetapkan lain.

## Yang membutuhkan perhatian (decision support)

`health.keputusan()` hanya memunculkan item bila datanya nyata: kategori Kritis / Perlu Keputusan / Perlu Follow-up / Data Issue / Positive Trend,
masing-masing dengan isu, dampak, metrik, nilai sekarang & sebelumnya, tren, jumlah terkena, kemungkinan sebab, tindakan, tautan, dan sumber.

## Batasan

- PDF dibuat dari dialog cetak browser (tombol "Cetak / PDF", tata letak A4); belum ada pembuat PDF di server.
- "Kirim ke orang tua" membuka WhatsApp dengan pesan terisi (hanya untuk peran yang boleh melihat kontak); tidak mengirim otomatis.
- Bulan sesudah riwayat DB Murid (Okt 2026 dst.) memakai STATUS_EVENT / Status Awal; tanpa event baru, status sama dengan Sep 2026.
- Tagihan resmi, tunggakan per tagihan, dan verifikasi bukti bayar baru berisi setelah BULAN BARU & verifikasi Finance dibangun (SPP_TAGIHAN / BUKTI_BAYAR masih kosong).
