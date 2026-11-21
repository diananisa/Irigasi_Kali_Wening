# Kondisi Jaringan Irigasi

Aplikasi web untuk menampilkan kondisi jaringan irigasi, data bangunan, saluran, petak tersier, dampak kerusakan, prioritas pemeliharaan, dan kualitas data.

## Teknologi

- Frontend: React.js, Vite, Leaflet
- Backend: Python, FastAPI
- Database pendukung: PostgreSQL
- Geospatial: GeoPandas/Shapely, PyProj
- Graph processing: NetworkX
- Container: Docker Compose

## Persyaratan

- Docker
- Docker Compose
- Git

## Menjalankan Aplikasi

Clone repository:

```bash
git clone <URL_REPOSITORY>
cd irigasi-kali-wening
```

Jalankan aplikasi:

```bash
docker compose up -d --build
```

Periksa container:

```bash
docker compose ps
```

Akses aplikasi melalui:

- Frontend: http://localhost:8080
- API: http://localhost:8080/api

## Fitur

1. Dashboard ringkasan kondisi jaringan irigasi.
2. Peta jaringan irigasi dengan warna kondisi saluran dan simbol bangunan.
3. Informasi detail bangunan dan riwayat pemeriksaan.
4. Perhitungan dampak kerusakan terhadap petak tersier.
5. Prioritas rehabilitasi berdasarkan kondisi dan luas dampak.
6. Identifikasi kualitas dan anomali data.
7. Impor laporan pemeriksaan susulan melalui API.

## Endpoint API

| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/api/health` | Status aplikasi |
| GET | `/api/versi` | Versi kontrak API |
| GET | `/api/aset` | Daftar aset |
| GET | `/api/aset/{kode_aset}` | Detail aset |
| GET | `/api/aset/{kode_aset}/dampak` | Dampak aset |
| GET | `/api/saluran` | Data saluran |
| GET | `/api/petak` | Data petak tersier |
| GET | `/api/rekap/saluran` | Rekap kondisi saluran |
| GET | `/api/prioritas` | Prioritas pemeliharaan |
| GET | `/api/kualitas-data` | Temuan kualitas data |
| POST | `/api/impor/susulan` | Impor laporan susulan |

## Impor Laporan Susulan

Gunakan endpoint:

```text
POST /api/impor/susulan
```

Kirim file Excel `.xlsx` menggunakan multipart form dengan nama field `file`.

Sistem mengidentifikasi laporan baru, diperbarui, dibatalkan, dan tidak berubah. Data dihitung ulang apabila terdapat perubahan.

## Menghentikan Aplikasi

```bash
docker compose down
```

Untuk melihat log:

```bash
docker compose logs -f
```