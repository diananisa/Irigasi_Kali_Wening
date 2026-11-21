import os
import tempfile
import json

from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from shapely.geometry import mapping
from app.data_service import muat_data, DATA_DIR
from geospatial import transformer_wgs84_to_utm
from shapely.ops import transform
from cleaning import bersihkan_laporan
from datetime import date


app = FastAPI(
    title="Sistem Informasi Jaringan Irigasi",
    description="Aplikasi monitoring kondisi jaringan irigasi Kali Wening",
    version="1.0.0"
)


status_aplikasi = "memuat"
data_irigasi = {}
pesan_error = None

laporan_susulan_importadas = {}
FILE_LAPORAN_SUSULAN = DATA_DIR / "laporan_susulan_import.json"


@app.on_event("startup")
def startup_event():
    global status_aplikasi, data_irigasi, pesan_error
    global laporan_susulan_importadas

    try:
        print("Memuat dan memproses data irigasi...")

        # Muat laporan susulan yang pernah diimpor
        if FILE_LAPORAN_SUSULAN.exists():
            with open(FILE_LAPORAN_SUSULAN, "r", encoding="utf-8") as file:
                laporan_susulan_importadas = json.load(file)

            # Kembalikan tanggal dari string menjadi datetime.date
            for item in laporan_susulan_importadas.values():
                tanggal = item.get("tanggal")

                if isinstance(tanggal, str) and tanggal:
                    item["tanggal"] = date.fromisoformat(tanggal)
        else:
            laporan_susulan_importadas = {}

        # Muat ulang seluruh data dengan laporan susulan
        data_irigasi = muat_data(
            laporan_tambahan=list(laporan_susulan_importadas.values())
        )

        status_aplikasi = "siap"

        print("Data irigasi berhasil dimuat.")

    except Exception as error:
        status_aplikasi = "error"
        pesan_error = str(error)

        print("Gagal memuat data:", pesan_error)

@app.post("/api/impor/susulan")
async def impor_laporan_susulan(file: UploadFile = File(...)):
    global data_irigasi, laporan_susulan_importadas

    # Validasi format file
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="File harus berformat .xlsx"
        )

    isi_file = await file.read()

    if not isi_file:
        raise HTTPException(
            status_code=400,
            detail="File yang diunggah kosong."
        )

    if len(isi_file) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Ukuran file maksimal 10 MB."
        )

    # Baca dan bersihkan laporan Excel
    path_sementara = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".xlsx",
            delete=False
        ) as file_sementara:
            file_sementara.write(isi_file)
            path_sementara = file_sementara.name

        laporan_masuk = bersihkan_laporan(path_sementara)

        # Gunakan nama file asli sebagai sumber data
        for item in laporan_masuk:
            item["sumber"] = file.filename

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca file Excel: {str(error)}"
        )

    finally:
        if path_sementara and os.path.exists(path_sementara):
            os.remove(path_sementara)

    # Pastikan setiap laporan memiliki ID
    if any(not item.get("id_laporan") for item in laporan_masuk):
        raise HTTPException(
            status_code=400,
            detail="Terdapat laporan yang tidak memiliki id_laporan."
        )

    # Tolak ID ganda dalam satu file
    daftar_id = [item["id_laporan"] for item in laporan_masuk]

    if len(daftar_id) != len(set(daftar_id)):
        raise HTTPException(
            status_code=400,
            detail="Terdapat id_laporan duplikat dalam file."
        )

    # Data laporan yang sudah tersedia
    laporan_lama = {
        item["id_laporan"]: item
        for item in data_irigasi.get("laporan", [])
        if item.get("id_laporan")
    }

    laporan_susulan_baru = dict(laporan_susulan_importadas)

    hasil = {
        "baru": [],
        "diperbarui": [],
        "dibatalkan": [],
        "tidak_berubah": []
    }

    kolom_perbandingan = [
        "tanggal",
        "petugas",
        "nomenklatur",
        "jenis_kerusakan",
        "kondisi",
        "lat",
        "lon",
        "status",
        "keterangan"
    ]

    ada_perubahan = False

    # Bandingkan berdasarkan ID laporan
    for item in laporan_masuk:
        kode = item["id_laporan"]
        sebelumnya = laporan_lama.get(kode)

        if sebelumnya is None:
            hasil["baru"].append(kode)
            laporan_susulan_baru[kode] = item
            ada_perubahan = True
            continue

        berubah = any(
            item.get(kolom) != sebelumnya.get(kolom)
            for kolom in kolom_perbandingan
        )

        if not berubah:
            hasil["tidak_berubah"].append(kode)
            continue

        if (
            item.get("status") == "batal"
            and sebelumnya.get("status") != "batal"
        ):
            hasil["dibatalkan"].append(kode)
        else:
            hasil["diperbarui"].append(kode)

        laporan_susulan_baru[kode] = item
        ada_perubahan = True

    # Hitung ulang seluruh data jika terdapat perubahan
    if ada_perubahan:
        try:
            data_baru = muat_data(
                laporan_tambahan=list(laporan_susulan_baru.values())
            )

            # Simpan laporan susulan ke file sementara terlebih dahulu
            FILE_LAPORAN_SUSULAN.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            file_sementara = FILE_LAPORAN_SUSULAN.with_suffix(".tmp")

            with open(file_sementara, "w", encoding="utf-8") as file_json:
                json.dump(
                    laporan_susulan_baru,
                    file_json,
                    ensure_ascii=False,
                    indent=4,
                    default=lambda nilai: (
                        nilai.isoformat()
                        if hasattr(nilai, "isoformat")
                        else str(nilai)
                    )
                )

            # Ganti file lama setelah penyimpanan berhasil
            os.replace(file_sementara, FILE_LAPORAN_SUSULAN)

            # Perbarui data aplikasi setelah semuanya berhasil
            data_irigasi = data_baru
            laporan_susulan_importadas = laporan_susulan_baru

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Gagal memproses atau menyimpan laporan susulan: {str(error)}"
            )

    return {
        "status": "berhasil",
        "jumlah_diproses": len(laporan_masuk),
        "jumlah_baru": len(hasil["baru"]),
        "jumlah_diperbarui": len(hasil["diperbarui"]),
        "jumlah_dibatalkan": len(hasil["dibatalkan"]),
        "jumlah_tidak_berubah": len(hasil["tidak_berubah"]),
        "hasil": hasil,
        "data_dihitung_ulang": ada_perubahan,
        "total_aset": len(data_irigasi.get("aset", [])),
        "total_laporan": len(data_irigasi.get("laporan", [])),
        "total_prioritas": len(data_irigasi.get("prioritas", []))
    }

@app.get("/")
def root():
    return {
        "message": "API Irigasi Kali Wening Berjalan"
    }


@app.get("/api/health")
def health():
    return {
        "status": status_aplikasi,
        "error": pesan_error
    }


@app.get("/api/versi")
def versi():
    return {
        "versi_kontrak": "1.2"
    }

@app.get("/api/aset")
def daftar_aset(
    jenis: str = None,
    kondisi: str = None,
    saluran: str = None
):
    hasil = data_irigasi.get("aset", [])

    if jenis:
        hasil = [
            a for a in hasil
            if jenis.lower() in str(a.get("jenis", "")).lower()
        ]

    if kondisi:
        hasil = [
            a for a in hasil
            if kondisi.lower() in str(a.get("kondisi", "")).lower()
        ]

    if saluran:
        hasil = [
            a for a in hasil
            if saluran.lower() in str(a.get("nama_saluran", "")).lower()
        ]

    return {
        "total": len(hasil),
        "data": hasil
    }

@app.get("/api/aset/{kode_aset}")
def detail_aset(kode_aset: str):
    # Cari identitas bangunan
    aset = next(
        (
            a for a in data_irigasi.get("aset", [])
            if a.get("kode_aset") == kode_aset
        ),
        None
    )

    if aset is None:
        raise HTTPException(
            status_code=404,
            detail="Aset tidak ditemukan"
        )

    # Cari hubungan petak tersier dengan bangunan sadap
    hubungan_petak = [
        hubungan
        for hubungan in data_irigasi.get("hubungan_petak", [])
        if hubungan.get("kode_aset_sadap") == kode_aset
    ]

    # Cari hasil analisis dampak bangunan
    dampak = next(
        (
            item
            for item in data_irigasi.get("dampak", [])
            if item.get("kode_aset") == kode_aset
        ),
        None
    )

    # Cari hasil prioritas rehabilitasi
    prioritas = next(
        (
            item
            for item in data_irigasi.get("prioritas", [])
            if item.get("kode_aset") == kode_aset
        ),
        None
    )

    # Riwayat laporan pemeriksaan aset
    riwayat_laporan = [
        laporan
        for laporan in data_irigasi.get("laporan", [])
        if laporan.get("kode_aset") == kode_aset
    ]

    riwayat_laporan.sort(
        key=lambda item: str(item.get("tanggal") or ""),
        reverse=True
    )

    return {
        "data": aset,
        "hubungan_petak": hubungan_petak,
        "dampak": dampak,
        "prioritas": prioritas,
        "riwayat_laporan": riwayat_laporan
    }

@app.get("/api/aset/{kode_aset}/dampak")
def dampak_aset(kode_aset: str):
    # Pastikan aset tersedia
    aset = next(
        (
            item for item in data_irigasi.get("aset", [])
            if item.get("kode_aset") == kode_aset
        ),
        None
    )

    if aset is None:
        raise HTTPException(
            status_code=404,
            detail="Aset tidak ditemukan"
        )

    # Ambil hubungan petak tersier
    hubungan_petak = [
        item
        for item in data_irigasi.get("hubungan_petak", [])
        if item.get("kode_aset_sadap") == kode_aset
    ]

    # Ambil hasil analisis dampak
    dampak = next(
        (
            item
            for item in data_irigasi.get("dampak", [])
            if item.get("kode_aset") == kode_aset
        ),
        None
    )

    # Ambil hasil prioritas rehabilitasi
    prioritas = next(
        (
            item
            for item in data_irigasi.get("prioritas", [])
            if item.get("kode_aset") == kode_aset
        ),
        None
    )

    return {
        "kode_aset": kode_aset,
        "dampak": dampak,
        "hubungan_petak": hubungan_petak,
        "prioritas": prioritas
    }

def buat_feature_collection(daftar_data):
    features = []

    for item in daftar_data:
        geometry = item.get("geometry")

        if geometry is None or geometry.is_empty:
            continue

        properties = {
            key: value
            for key, value in item.items()
            if key != "geometry"
        }

        features.append({
            "type": "Feature",
            "geometry": mapping(geometry),
            "properties": properties
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


@app.get("/api/saluran")
def daftar_saluran():
    return buat_feature_collection(
        data_irigasi.get("saluran", [])
    )

@app.get("/api/rekap/saluran")
def rekap_saluran():
    saluran = data_irigasi.get("saluran", [])

    ringkasan = {}
    total_panjang_km = 0
    jumlah_geometri_valid = 0

    for item in saluran:
        tingkat = item.get("tingkat", "tidak diketahui")
        kondisi = item.get("kondisi", "tidak diketahui")

        if tingkat not in ringkasan:
            ringkasan[tingkat] = {
                "jumlah": 0,
                "kondisi": {}
            }

        ringkasan[tingkat]["jumlah"] += 1
        ringkasan[tingkat]["kondisi"][kondisi] = (
            ringkasan[tingkat]["kondisi"].get(kondisi, 0) + 1
        )

        geometry = item.get("geometry")

        if geometry is not None and not geometry.is_empty and geometry.is_valid:
            geometry_utm = transform(
                transformer_wgs84_to_utm.transform,
                geometry
            )

            total_panjang_km += geometry_utm.length / 1000
            jumlah_geometri_valid += 1

    return {
        "total_saluran": len(saluran),
        "jumlah_geometri_valid": jumlah_geometri_valid,
        "total_panjang_km": round(total_panjang_km, 2),
        "ringkasan": ringkasan
    }


@app.get("/api/petak")
def daftar_petak():
    return buat_feature_collection(
        data_irigasi.get("petak", [])
    )

@app.get("/api/kualitas-data")
def kualitas_data():
    temuan = []

    # 1. Periksa koordinat dan jarak aset dari saluran
    for aset in data_irigasi.get("aset", []):
        kode = aset.get("kode_aset")
        sumber = aset.get("sumber")
        baris = aset.get("baris_sumber")

        status_koordinat = aset.get("status_koordinat")
        status_kedekatan = aset.get("status_kedekatan")

        if status_kedekatan == "koordinat_tidak_valid":
            temuan.append({
                "jenis_masalah": "koordinat_tidak_valid",
                "kategori": "aset",
                "kode": kode,
                "sumber": sumber,
                "baris_atau_fitur": baris,
                "detail": "Koordinat aset kosong atau tidak valid.",
                "saran_tindakan": "Periksa dan lengkapi koordinat pada data sumber."
            })

        elif status_koordinat == "koordinat_tertukar":
            temuan.append({
                "jenis_masalah": "koordinat_tertukar",
                "kategori": "aset",
                "kode": kode,
                "sumber": sumber,
                "baris_atau_fitur": baris,
                "detail": "Urutan koordinat terdeteksi tertukar.",
                "saran_tindakan": "Periksa kembali urutan longitude dan latitude."
            })

        elif status_kedekatan == "jauh_dari_saluran":
            temuan.append({
                "jenis_masalah": "jauh_dari_saluran",
                "kategori": "aset",
                "kode": kode,
                "sumber": sumber,
                "baris_atau_fitur": baris,
                "jarak_meter": aset.get("jarak_saluran_meter"),
                "detail": "Lokasi aset berjarak lebih dari 50 meter dari saluran terdekat.",
                "saran_tindakan": "Verifikasi koordinat aset dan posisi saluran."
            })

    # 2. Periksa duplikasi aset
    for kelompok in data_irigasi.get("duplikat_aset", []):
        for aset in kelompok.get("data_duplikat", []):
            temuan.append({
                "jenis_masalah": "duplikasi_aset",
                "kategori": "aset",
                "kode": kelompok.get("kode_aset"),
                "sumber": aset.get("sumber"),
                "baris_atau_fitur": aset.get("baris_sumber"),
                "detail": "Data aset duplikat. Data terbaru dipertahankan.",
                "saran_tindakan": "Periksa data sumber dan pastikan tidak ada pencatatan ganda."
            })

    # 3. Periksa duplikasi saluran
    for saluran in data_irigasi.get("duplikat_saluran", []):
        temuan.append({
            "jenis_masalah": "duplikasi_saluran",
            "kategori": "saluran",
            "kode": saluran.get("id_ruas"),
            "sumber": saluran.get("sumber"),
            "baris_atau_fitur": saluran.get("fitur_sumber"),
            "detail": (
                f"Geometri saluran identik dengan "
                f"{saluran.get('duplikat_dari')}."
            ),
            "saran_tindakan": "Periksa geometri dan identitas ruas saluran."
        })

    # 4. Periksa duplikasi laporan
    for laporan_duplikat in data_irigasi.get("duplikat_laporan", []):
        laporan = laporan_duplikat.get("data", {})

        temuan.append({
            "jenis_masalah": "duplikasi_laporan",
            "kategori": "laporan",
            "kode": laporan.get("kode_aset"),
            "sumber": laporan.get("sumber"),
            "baris_atau_fitur": laporan.get("baris_sumber"),
            "detail": "Ditemukan laporan pemeriksaan duplikat.",
            "saran_tindakan": "Periksa laporan dengan aset, tanggal, dan jenis kerusakan yang sama."
        })

    for laporan in data_irigasi.get("laporan", []):
        if laporan.get("status_pencocokan") == "tidak_terhubung":
            temuan.append({
                "jenis_masalah": "laporan_tidak_terhubung",
                "kategori": "laporan",
                "kode": laporan.get("id_laporan"),
                "sumber": laporan.get("sumber"),
                "baris_atau_fitur": laporan.get("baris_sumber"),
                "nomenklatur": laporan.get("nomenklatur"),
                "tanggal": laporan.get("tanggal"),
                "status_koordinat": laporan.get("status_koordinat_laporan"),
                "detail": "Laporan tidak berhasil dihubungkan dengan aset.",
                "saran_tindakan": (
                    "Periksa nomenklatur, koordinat, dan identitas aset "
                    "pada data sumber."
                )
            })

    # 5. Periksa duplikasi petak tersier
    kualitas_petak = data_irigasi.get("kualitas_petak", {})

    for petak in kualitas_petak.get("duplikat_detail", []):
        temuan.append({
            "jenis_masalah": "duplikasi_petak",
            "kategori": "petak",
            "kode": petak.get("kode_petak"),
            "sumber": petak.get("sumber"),
            "baris_atau_fitur": petak.get("fitur_sumber"),
            "detail": "Ditemukan fitur petak tersier dengan kode yang sama.",
            "saran_tindakan": "Periksa geometri dan identitas petak pada data sumber."
        })

    # 6. Periksa geometri petak yang gagal
    for petak in kualitas_petak.get("geometri_gagal_detail", []):
        temuan.append({
            "jenis_masalah": "geometri_gagal",
            "kategori": "petak",
            "kode": petak.get("kode_petak"),
            "sumber": petak.get("sumber"),
            "baris_atau_fitur": petak.get("fitur_sumber"),
            "detail": "Geometri petak gagal diproses.",
            "saran_tindakan": "Periksa dan perbaiki geometri pada data sumber."
        })

    # 7. Periksa anomali luas petak
    for petak in data_irigasi.get("petak", []):
        if petak.get("anomali"):
            temuan.append({
                "jenis_masalah": "anomali_luas_petak",
                "kategori": "petak",
                "kode": petak.get("kode_petak"),
                "sumber": petak.get("sumber"),
                "baris_atau_fitur": petak.get("fitur_sumber"),
                "detail": (
                    f"Selisih luas geometri dan luas baku "
                    f"sebesar {petak.get('selisih_persen')}%."
                ),
                "luas_geometri_ha": petak.get("luas_geometri_ha"),
                "luas_baku_ha": petak.get("luas_baku_ha"),
                "saran_tindakan": "Verifikasi luas geometri dan luas baku petak."
            })

    # Ringkasan jumlah temuan berdasarkan jenis masalah
    ringkasan = {}

    for item in temuan:
        jenis = item["jenis_masalah"]
        ringkasan[jenis] = ringkasan.get(jenis, 0) + 1

    return {
        "total_temuan": len(temuan),
        "ringkasan": ringkasan,
        "data": temuan
    }

@app.get("/api/prioritas")
def daftar_prioritas():
    return {
        "total": len(data_irigasi.get("prioritas", [])),
        "data": data_irigasi.get("prioritas", [])
    }
