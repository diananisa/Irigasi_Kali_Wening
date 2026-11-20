from fastapi import FastAPI, HTTPException
from shapely.geometry import mapping

from backend.app.data_service import muat_data

app = FastAPI(
    title="Sistem Informasi Jaringan Irigasi",
    description="Aplikasi monitoring kondisi jaringan irigasi Kali Wening",
    version="1.0.0"
)


status_aplikasi = "loading"
data_irigasi = {}
pesan_error = None


@app.on_event("startup")
def startup_event():
    global status_aplikasi, data_irigasi, pesan_error

    try:
        print("Memuat dan memproses data irigasi...")

        data_irigasi = muat_data()

        status_aplikasi = "ready"

        print("Data irigasi berhasil dimuat.")

    except Exception as error:
        status_aplikasi = "error"
        pesan_error = str(error)

        print("Gagal memuat data:", pesan_error)


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

    return {
        "data": aset,
        "hubungan_petak": hubungan_petak,
        "dampak": dampak,
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


@app.get("/api/petak")
def daftar_petak():
    return buat_feature_collection(
        data_irigasi.get("petak", [])
    )
