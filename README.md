# Wedding scraper — Google Maps (Ciamis)

Crawler Python yang memburu usaha **jasa wedding** di sekitar **Ciamis** lewat pencarian Google Maps, lalu menyimpan hasilnya ke JSON:

```
data/wedding-organizer-ciamis.json
```

Tidak butuh dependency tambahan — murni stdlib (`urllib`, `json`, `re`). Tidak perlu API key.

## Cara pakai

```sh
python3 scraper.py
```

Hasil ditulis ke `data/wedding-organizer-ciamis.json` (format JSON sama seperti sebelumnya, ditambah field bonus dari listing Google Maps).

Opsi CLI:

```sh
python3 scraper.py --keywords "jasa wedding ciamis,rias pengantin ciamis"
python3 scraper.py --region "Kabupaten Ciamis" --output-dir data
python3 scraper.py --no-pin   # tanpa paku koordinat, biar Google tentukan area
```

## Konfigurasi kata kunci

Edit `gmaps-config.json`:

- `region` — label wilayah untuk laporan.
- `center` / `zoom` — paku koordinat + level zoom pencarian (default: pusat Ciamis, z12).
- `keywords` — daftar kata kunci. Bebas mainkan kata-katanya; setiap kata kunci menghasilkan sampai 20 hasil, lalu diduplikasi otomatis berdasarkan nama + alamat + ID tempat Google.

Setiap kata kunci diambil dengan jeda acak 6–12 detik supaya lembut ke Google. Kalau kena blokir/rate-limit, template parameter `pb` (`gmaps-pb-template.txt`) di-refresh otomatis dari halaman Google Maps dan kata kunci dicoba ulang; yang tetap gagal dilaporkan (`[skip] ...`) lalu lanjut ke berikutnya.

## Format JSON

Struktur per baris:

```json
{
  "id_sumber": "gmaps:ChIJ...",        // ID tempat Google Maps
  "nama": "Masagi Wedding Organizer",
  "alamat": "Perum Lembah Medina E05, ...",
  "telepon_bisnis": "0823-1090-0467",
  "wilayah_layanan": null,
  "situs_web": "http://linktr.ee/masagi...",
  "status_situs": "tercantum",          // "tercantum" / "tidak_tercantum"
  "tanggal_dicek_situs": "2025-...",
  "sumber": { "nama": "Google Maps", "url": "https://www.google.com/maps" },
  "dicek_pada": "2025-...",
  "kategori": "Perencana Pernikahan",
  "rating": 4.7,
  "jumlah_ulasan": 15,
  "koordinat": { "lat": -7.3443815, "lon": 108.3390112 },
  "nama_daerah": "Linggasari, Kecamatan Ciamis",
  "google_maps_url": "https://www.google.com/maps/search/?api=1&query=..."
}
```

Note: `status_situs` hanya menandai ada/tidaknya `situs_web` yang tertera di listing — tidak ada pengecekan HTTP ke situs luar.