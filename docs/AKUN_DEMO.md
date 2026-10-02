# Akun demo (laptop)

Akun demo dipakai untuk mencoba aplikasi sendiri di laptop. **Jangan aktifkan di server** — pemeriksaan sistem `spi.E001`
menolak `DEMO_ACCOUNTS=True` tanpa `DEBUG=True`.

## Menyalakan

1. Di `.env`: `DEBUG=True` dan `DEMO_ACCOUNTS=True`.
2. Pastikan cabang SPI-JKT (dan SPI-AS) sudah diimpor (lihat README).
3. `.venv/Scripts/python manage.py seed_demo_accounts` — membuat/memperbarui akun di bawah. Bila `DEMO_PASSWORD` di `.env`
   kosong, kata sandi acak dibuat dan ditulis ke `.env`. Perintah boleh diulang.
4. Halaman Masuk menampilkan panel **Akun demo**: klik peran untuk langsung masuk; atau masuk biasa dengan email di bawah dan
   kata sandi `DEMO_PASSWORD` dari `.env`.

| Email | Peran | Cabang | Yang terlihat |
|---|---|---|---|
| superadmin@spi.local | Super Admin | semua | semua halaman, menu Cabang |
| admin.jkt@spi.local | Branch Admin | SPI Jakarta | Beranda, Laporan, Impor Data, Pengguna |
| manager.jkt@spi.local | Manager | SPI Jakarta | Beranda, Laporan |
| cso.jkt@spi.local | CSO | SPI Jakarta | Beranda, Laporan |
| finance.jkt@spi.local | Finance | SPI Jakarta | Beranda, Laporan |
| academic.jkt@spi.local | Academic | SPI Jakarta | Beranda, Laporan |
| guru.jkt@spi.local | Teacher | SPI Jakarta | belum ada halaman (tahap jadwal guru) — tampil "tidak punya akses" |
| admin.as@spi.local | Branch Admin | SPI Alam Sutera | cabang tanpa data operasional: angka nol / "—" |

Mematikan: hapus `DEMO_ACCOUNTS` dari `.env` (panel hilang, masuk satu klik ditolak). Akun tetap ada sampai dinonaktifkan di
halaman Pengguna & Akses.
