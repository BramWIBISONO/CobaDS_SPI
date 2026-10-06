# Validasi Student Lifecycle

## Sumber dan pemetaan

- Status historis berasal dari `DBulan` (`D_BULAN`) dengan kunci `ID v1|yyyymm`, sama dengan sumber yang dipakai Laporan Murid.
- `A`, `B`, `R`, `C`, dan `O` masing-masing berarti Aktif, Baru, Rejoin, Cuti, dan Off.
- Baris `D_BULAN` yang ada dengan status kosong dipetakan menjadi `?`. Baris bulan yang tidak ada mengikuti rumus MATRIKS: `–` sebelum murid tercatat, `·` setelah Off, selain itu `?`.
- Status teks nonkosong yang tidak termasuk Aktif/Baru/Rejoin/Cuti/Off juga menjadi `–`, mengikuti `IFERROR(CHOOSE(MATCH(...)))` di Excel. Tidak ada status tak dikenal pada nilai status D_BULAN workbook Jakarta yang divalidasi.
- Status sesudah Sep 2026 diturunkan dari `STATUS_EVENT`; bila tidak ada event, gunakan `Status Awal`. Untuk bulan berjalan hanya event sampai tanggal hari ini yang dihitung.
- “Bulan aktif” mengikuti rumus workbook, yaitu jumlah `A/B/R` pada Jan 2024–Sep 2026. Properti terpisah menghitung sampai periode matriks aplikasi saat ini.
- Rumus retensi/churn bukan rumus resmi di D_BULAN. Definisi analitisnya ditampilkan di halaman Lifecycle dan tidak diberi label angka Excel resmi.

## Hasil validasi sumber

Validasi Jakarta pada data lokal: 323 baris MATRIKS yang memiliki formula menghasilkan 10.659 sel historis, dengan 0 perbedaan status, 0 perbedaan hitungan Bulan Aktif, dan 0 perbedaan status terakhir historis. Snapshot memiliki 324 ID di D_MURID dan 324 murid di STUDENT_MASTER; ID M324 tidak memiliki baris formula MATRIKS karena rentang formula sheet berhenti satu murid lebih awal. Aplikasi tetap menampilkan murid itu dari data operasional.

Tes lambat `dashboards/tests/test_golden.py::test_management_lifecycle_matrix_matches_matriks_excel` mengulang perbandingan semua sel historis, hitungan bulan aktif, dan status terakhir historis dengan nilai tersimpan (cached) di sheet `MATRIKS`. Perbedaan cakupan baris formula dengan D_MURID dicatat sebagai keterbatasan workbook, bukan disamarkan sebagai hasil validasi.

Rujukan Excel yang dipakai adalah workbook Jakarta v4 yang juga dipakai tes golden. Tes memakai nilai hasil formula yang tersimpan dalam workbook; ia tidak membuka ulang Excel atau menghitung ulang formula.

## Batasan

- Tren setelah Sep 2026 bergantung pada kelengkapan dan tanggal efektif `STATUS_EVENT`; event yang belum tercatat tidak dapat disimpulkan dari data.
- Workbook MATRIKS hanya berisi rentang riwayat tetap. Murid pada data operasional yang tidak mempunyai baris formula di MATRIKS tetap ditampilkan oleh aplikasi dan tidak dapat dibandingkan dengan sel Excel yang tidak tersedia.
- Retensi dan churn masih definisi analitis yang eksplisit, bukan KPI resmi yang sudah disahkan.
