# Design system SPI Super App

Berlaku sejak UI/UX overhaul (6 Okt 2026). Sumber: `assets/app.css` (Tailwind v4, `npm run build:css`). Contoh hidup semua
komponen: halaman **UI Kit** (`/ui-kit/`, menu Admin, untuk Branch Admin). Semua modul memakai komponen yang sama - jangan membuat
gaya sendiri per halaman.

## Prinsip
- Netral & tenang; **biru SPI** jadi jangkar visual. Warna kuat hanya untuk aksi utama, status aktif, status, dan angka yang
  menuntut perhatian. Tidak ada warna berbeda per kartu.
- Pekerjaan lebih dulu dari analitik (Beranda = Command Center: perlu tindakan → hari ini → angka kunci → akademik → keuangan → aktivitas).
- Tidak semua hal adalah kartu; kartu hanya untuk mengelompokkan informasi atau aksi. Tidak ada kartu di dalam kartu di dalam kartu.
- Ponsel bukan desktop yang dikecilkan: laci menu, kartu bertumpuk, agenda pengganti kisi kalender, tombol sentuh 40px.

## Token (`@theme`)
| Kelompok | Token | Nilai / pemakaian |
|---|---|---|
| Merek | `brand-500` / `brand-900` / `accent-400` | #176DF8 aksi utama · #041A5A merek gelap · #FFC928 sorotan hemat |
| Netral | `canvas`, `surface`, `subtle`, `line`, `line-strong` | latar aplikasi #F4F6FA, kartu putih, latar sekunder, garis halus |
| Teks | `ink`, `ink-2`, `muted` #5F6B84, `faint` #69748C | judul/teks utama navy, isi, sekunder, metadata - semua >= 4.5:1 di putih (muted juga di canvas) |
| Isian | `line-input` #8A94A7 | garis kotak isian & centang >= 3:1 (WCAG 1.4.11); kartu tetap memakai `line` yang halus |
| Semantik | `success-*`, `warning-*`, `danger-*` (+ `brand` = info) | lembut: latar 50, garis 100, teks 600/700 |
| Radius | `sm 6 · md 8 · lg 10 · xl 14 · 2xl 18` | makin dalam makin kecil (kartu 18, tombol 10, badge pill) |
| Bayangan | `shadow-xs/sm/md/lg` | sangat lembut, diwarnai navy |
| Font | Inter Variable (lokal, `static/vendor/fonts`) | judul halaman 26/600, bagian 15/600, isi 14, metadata 13, KPI 28/600 tabular |
| Spasi | skala Tailwind 4px | 4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 |
| Z-index | `--z-topbar 30 · overlay 40 · sidebar 45 · menu 50 · toast 60` | jangan pakai angka acak |

## Komponen (kelas CSS)
- Kerangka: `.app-sidebar` (252px, bisa diciutkan ke 72px & diingat per peramban; laci di ponsel), `.app-topbar` (breadcrumb,
  pencarian global Ctrl+K, tombol **Tambah** sesuai izin, notifikasi, akun), `.page`.
- Header halaman: `{% pageheader title subtitle icon count %}…aksi…{% endpageheader %}`; breadcrumb dari variabel `crumbs`
  (desktop di topbar, ponsel jadi tautan kembali).
- Tombol: `.btn` + `.btn-primary | -secondary | -ghost | -danger | -danger-soft`, ukuran `.btn-sm | .btn-lg`, `.btn-icon`, `.btn-block`.
- Input: `.field` (select bergaya, `.is-invalid`/`aria-invalid`), `.field-label`, `.field-hint`, `.errorlist`, `.input-icon`, `.form-actions` (lengket di bawah).
- Badge status: `components/status_badge.html` (label ramah + titik warna; nilai asli di `title`), `.status-badge .st-baik|perhatian|serius|kritis|info|netral`.
- KPI: `components/kpi_card.html` (`emphasis=danger|warning` hanya bila perlu perhatian; `soon=True` = data belum ada).
- Tabel: `.table-wrap overflow-x-auto` + `.data-table` (baris tinggi, pemisah halus, hover), `.table-toolbar`, paginasi `components/pagination.html`.
- Navigasi lokal: `.tabs/.tab/.tab-active`, `.segmented` (tautan, tombol, atau radio), `.chip`.
- Menu: `<details data-menu>` + `.menu/.menu-item` (tutup otomatis saat klik di luar / Esc).
- Avatar: `.avatar` + filter `initials` & `avatar_tone` (6 nada lembut, tetap per nama).
- Status kosong / memuat / pesan: `components/empty_state.html`, `.skeleton`, `.callout-info|warning|danger|neutral`, toast (`SPI.toast(teks, jenis)`), dialog konfirmasi (`data-confirm="…"`).
- Kalender: `.cal`, `.cal-event .ev-P|G|F|S|X` (warna = tipe kelas dari huruf pertama kode), `.cal-now`, `.month-grid`; tata letak di `classes/calendar.py`.
- Kehadiran: `.att-options/.att-opt` (tombol besar Hadir/Terlambat/Izin/Tidak hadir).
- Keuangan (fondasi): `.money`, `.money-lg`, `.pay-paid|partial|pending|overdue|void`.

## Aksesibilitas (WCAG 2.1 AA)
- Kontras: teks kecil >= 4.5:1 (token di atas), garis isian >= 3:1, fokus keyboard = garis biru 2px (`:focus-visible`).
- Layar sentuh (`pointer: coarse`): tombol, menu, isian, pilihan kehadiran minimal 44px; chip & tombol kecil 40px.
- Status tidak hanya warna: badge selalu berteks; sesi yang perlu konfirmasi punya ikon jam + teks pembaca layar.
- Tautan "Lewati ke konten", satu `<h1>` per halaman, landmark `header/nav/main/aside`, `lang="id"`.

## Aturan pakai
1. Halaman baru: `{% extends "base.html" %}`, `{% pageheader %}`, beri `crumbs` dari view.
2. Angka: `|angka`, `|rp` (int, float, Decimal), kelas `tabular-nums`.
3. Setiap daftar punya status kosong; setiap aksi berbahaya memakai `data-confirm`; setiap tabel di dalam wadah `overflow-x-auto`.
4. Jangan menambah warna di luar token. Jangan mengulang informasi yang sama di dua tempat di layar yang sama.
