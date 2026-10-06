# Kritik desain & UX - UI/UX overhaul Super App (6 Okt 2026)

Cakupan: Beranda (Command Center), Murid (daftar & profil), Orang Tua, Kelas, Sesi (kalender), alur absensi guru, pencarian
global, UI Kit, Laporan - di 390 / 768 / 1440 px dengan data nyata SPI Jakarta (akun demo Branch Admin dan Teacher).
Metode: tangkapan layar Chrome headless, audit DOM otomatis per halaman (label isian, nama kontrol, alt, ID ganda, heading,
landmark, ukuran target), hitung rasio kontras token, uji interaksi nyata (pencarian, "Sisanya hadir"), seluruh uji otomatis.

## Ringkasan
Bahasa desain sudah konsisten (satu set token, komponen bersama, tidak ada warna per kartu) dan hierarki halaman jelas: aksi
utama satu tombol biru per halaman, pekerjaan mendesak tampil sebelum angka. Temuan terbesar ada di aksesibilitas tingkat
token (kontras teks metadata & garis isian) dan ergonomi sentuh - keduanya sudah diperbaiki di sumbernya (token & media
query), sehingga berlaku di semua halaman sekaligus.

## Audit design system
| Pemeriksaan | Hasil |
|---|---|
| Font | Inter di semua halaman (termasuk grafik Chart.js); tidak ada sisa Plus Jakarta Sans |
| Warna | 0 sisa `slate/emerald/amber/tone-*` di template; semua lewat token |
| Komponen | semua halaman memakai `pageheader`, `.card`, `.data-table`, `status_badge`, `kpi_card`, `empty_state` |
| Ikon | Tabler outline satu ketebalan di semua modul |
| Pelanggaran tersisa | tidak ada yang ditemukan |

## Aksesibilitas (WCAG 2.1 AA)
| Kriteria | Sebelum | Tindakan | Sesudah |
|---|---|---|---|
| 1.4.3 kontras teks - `faint` (label grup menu, jam kalender, waktu aktivitas) | 2.53:1 | token → #69748C | 4.69:1 |
| 1.4.3 kontras teks - `muted` di latar abu (canvas, badge netral) | 4.31-4.47:1 | token → #5F6B84 | 4.78-5.35:1 |
| 1.4.11 kontras garis kotak isian | 1.38:1 | token baru `line-input` #8A94A7 | 3.05:1 |
| 1.4.1 jangan hanya warna - sesi "perlu konfirmasi" di kalender | cincin oranye saja | ikon jam + teks pembaca layar | lulus |
| 1.3.1 / 4.1.2 label & nama | - | audit 11 halaman × 2 lebar: 0 isian tanpa label, 0 kontrol tanpa nama, 0 gambar tanpa alt, 0 ID ganda | lulus |
| 2.4.1 / 2.4.6 navigasi | - | tautan "Lewati ke konten", 1 `<h1>`, heading tidak melompat, landmark lengkap, `lang="id"` | lulus |
| 2.4.7 fokus terlihat | - | `:focus-visible` garis biru 2px global, cincin pada tombol & isian | lulus |
| Kontras lain | - | putih di biru SPI 4.59, tautan 5.62, badge status 5.4-7.1, aksen kuning di navy 10.5 | lulus |

Target sentuh (2.5.5 AAA / 2.5.8 di WCAG 2.2, tidak wajib di 2.1 AA): di ponsel 19-35 kontrol per halaman < 40px. Diperbaiki
untuk perangkat sentuh (`pointer: coarse`): tombol, menu, isian, pilihan kehadiran 44px; chip & tombol kecil 40px; kotak centang 22px.

## Kritik per halaman
| Halaman | Yang berhasil | Temuan | Status |
|---|---|---|---|
| Beranda | "Perlu tindakan" adalah hal pertama yang terbaca, berurutan bahaya → peringatan → info, setiap baris punya tombol aksi | Di desktop kartu aksi bisa lebih pendek dari kartu jadwal (ruang kosong) | diterima (konten nyata berubah tiap hari) |
| Daftar murid | segmen status berjumlah, pencarian langsung, aksi baris & massal | Di ponsel segmen status terpotong ke samping | diperbaiki: dibungkus 2 baris |
| Profil murid | header 360° (status, kelas, guru, aksi cepat), angka ringkas | 10 tab menggulir tanpa petunjuk di ponsel | diperbaiki: di ponsel menjadi pilihan "Bagian profil" |
| Orang tua | kartu anak dengan status, kelas, guru; kontak darurat terpisah | - | - |
| Kelas | kartu dengan bilah keterisian & jadwal, toggle tabel | - | - |
| Kalender | warna tipe + kode kelas (tidak bergantung warna), garis "sekarang", "+N" ke tampilan hari | penanda "perlu konfirmasi" hanya warna | diperbaiki (ikon + teks) |
| Absensi guru | 3 ketukan dari Jadwal Saya ke simpan, "Sisanya hadir", penghitung, tombol simpan lengket | label "Tidak hadir" terbungkus di 390px | diterima (tetap terbaca, target 44px) |
| Pencarian global | hasil per kelompok dengan avatar & status, Ctrl+K, panah atas/bawah | panel sempit memotong subjudul | diperbaiki: panel 30rem |
| Laporan, UI Kit | kartu KPI netral, grafik satu palet, contoh komponen Keuangan berlabel "bukan data" | - | - |

## Jawaban pertanyaan tinjauan
- Command Center: ya - judul, jumlah, dan tombol aksi tiap item terbaca dalam satu pandangan; ringkasan kalimat di atas menyebut "4 hal perlu tindakan".
- Alur absensi: tidak perlu digabung - Jadwal Saya → Absensi → tandai (atau "Sisanya hadir") → Simpan; itu minimum yang aman.
- 10 tab profil: di desktop jelas (satu baris, tab follow-up berjumlah); di ponsel sekarang pilihan tunggal.
- "+N sesi": konteks tetap (jam & hari benar, judul memuat daftar kode), satu klik ke tampilan hari yang menampilkan semuanya.
- Peran Orang tua & Murid: belum ada portal untuk peran itu di aplikasi (peran yang ada: Super Admin, Branch Admin, Manager,
  CSO, Finance, Academic, Teacher) - tidak dinilai.

## Prioritas
- Wajib (sudah dikerjakan): kontras token teks & isian; penanda non-warna di kalender; target sentuh di perangkat sentuh;
  navigasi profil di ponsel; segmen status di ponsel.
- Sebaiknya (berikutnya): pesan error form dihubungkan dengan `aria-describedby` secara eksplisit (Django sudah memberi
  `aria-invalid`); umumkan hasil pencarian global lewat `aria-live` untuk pembaca layar; ruang kosong kartu aksi di Beranda.
- Bagus bila ada: mode gelap; pintasan keyboard untuk navigasi kalender (← →).
