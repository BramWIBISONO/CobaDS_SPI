# Final project → sertifikat & Student Report otomatis

Menu **Akademik → Final Project & Sertifikat** (`/akademik/final-project/`), dan tab **Akademik** di profil murid.

## Alur
1. **Ajukan** (izin `project.submit`: Branch Admin, Manager, Academic) - profil murid → tab Akademik → *Final project selesai*.
   Isi: judul, tanggal presentasi, link, deskripsi, nilai rubrik 0-100 (pemahaman konsep, logika & problem solving, kreativitas,
   presentasi), kekuatan, yang perlu ditingkatkan, catatan untuk orang tua, rekomendasi level berikutnya (otomatis dari PROGRAM_MASTER).
   Level yang diselesaikan = level murid saat ini. Satu level hanya bisa diajukan sekali selama masih menunggu / sudah disetujui.
2. **Setujui / tolak** (izin `project.approve`: Branch Admin, Manager; Super Admin semua cabang). Rata-rata rubrik harus ≥ 70
   (`akademik/models.py` `LULUS_MIN`). Penolakan wajib beralasan; guru bisa mengajukan ulang. Menu menampilkan jumlah yang menunggu.
3. **Otomatis saat disetujui** (satu transaksi, diaudit):
   - Nomor sertifikat `SPI{level}-{tahun}{urut 3 digit}` - lanjut dari nomor tertinggi yang pernah terbit di cabang itu
     (aplikasi + riwayat "Sertifikat SPI" Excel di data murid), mis. sesudah `SPI21-2026007` → `SPI21-2026008`.
   - Sertifikat dari template level: PDF A4 landscape 300 dpi + JPG resolusi penuh + pratinjau.
   - Student Report (cetak / simpan PDF dari browser): data murid, project, rubrik & predikat, umpan balik, kehadiran, rekomendasi,
     perjalanan level, kolom tanda tangan guru & penyetuju.
   - Catatan AKADEMIK baru (progres 100%, kesimpulan LULUS, tautan report & sertifikat), "Sertifikat Terakhir" murid diperbarui.
   - Opsional: centang *naikkan murid ke level berikutnya* (memakai `change_program`, divalidasi PROGRAM_MASTER).

## Template sertifikat
Folder `CERT_TEMPLATE_DIR` (bawaan `app web/sertif/`). **Tidak disimpan di Git** (berisi tanda tangan; repo publik) - salin
manual ke server.

| Level | File | Isian |
|---|---|---|
| 1.0 | `sertifikat training 1.0.png` | nama (ruang di bawah judul), nomor (panel biru) |
| 1.1 | `sertifikat training 1.1.png` | nama, nomor |
| 2.1 | `2.1 Python.pptx` | kotak teks `nama`, `nomor`, `tanggal` - posisi/ukuran dibaca dari file |
| 2.2 | `2.2.pptx` | kotak teks `nama`, `nomor`, `tanggal keluar` |

Level lain (1.2, 2.0, 2.3, 2.4, …): persetujuan tetap jalan, nomor tercatat, Student Report dibuat; file sertifikat menyusul -
setelah template ditambahkan ke folder dan didaftarkan di `akademik/certificates.py` `TEMPLATES`, klik **Buat sertifikat** di
halaman final project (nomor & tanggal tetap). Template PPTX baru cukup memakai kotak teks berisi `nama`, `nomor`, `tanggal`.

Font: Arimo / Montserrat / Libre Baskerville (lisensi terbuka, `akademik/fonts/`; Libre Baskerville menggantikan Baskerville
Display PT yang berbayar). File hasil tersimpan di `MEDIA_ROOT/sertifikat/<kode cabang>/` dan hanya bisa diunduh pengguna cabang itu.
