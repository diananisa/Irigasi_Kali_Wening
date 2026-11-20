from pathlib import Path
from datetime import date, datetime

from cleaning import (
    bersihkan_aset,
    bersihkan_laporan,
    bersihkan_saluran,
    bersihkan_petak
)
from geospatial import (
    deduplikasi_saluran,
    bangun_graph_titik_sambungan,
    tentukan_arus_dari_bendung,
    hubungkan_bangunan_ke_saluran,
    hubungkan_laporan_ke_aset,
    proses_petak_tersier,
    hubungkan_petak_ke_sadap,
    hitung_dampak_bangunan,
    hitung_prioritas_rehabilitasi
)

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


def muat_data():
    # 1. Baca data sumber
    aset = bersihkan_aset(str(DATA_DIR / "aset_bangunan.csv"))
    laporan = bersihkan_laporan(str(DATA_DIR / "laporan_penelusuran.xlsx"))    
    saluran = bersihkan_saluran(str(DATA_DIR / "saluran.geojson"))
    petak = bersihkan_petak(str(DATA_DIR / "petak_tersier.geojson"))

    # 2. Deduplikasi saluran
    saluran, duplikat_saluran = deduplikasi_saluran(saluran)

    # 3. Bangun jaringan dan tentukan arah aliran
    graph, peta_ujung = bangun_graph_titik_sambungan(saluran)

    titik_bendung = peta_ujung[("KW-R01", 1)]

    arah_ruas = tentukan_arus_dari_bendung(
        graph,
        titik_bendung,
        peta_ujung
    )

    # 4. Hubungkan bangunan ke saluran
    aset = hubungkan_bangunan_ke_saluran(
        aset,
        saluran,
        arah_ruas
    )

    laporan_terhubung = hubungkan_laporan_ke_aset(
        laporan,
        aset
    )

        # 4b. Tentukan kondisi terbaru berdasarkan laporan aktif
    laporan_terbaru = {}

    for item in laporan_terhubung:
        kode_aset = item.get("kode_aset")

        if not kode_aset or item.get("status") != "aktif":
            continue

        tanggal = item.get("tanggal")

        if isinstance(tanggal, datetime):
            tanggal = tanggal.date()

        if isinstance(tanggal, str):
            tanggal = date.fromisoformat(tanggal)

        if not tanggal:
            continue

        sebelumnya = laporan_terbaru.get(kode_aset)

        if sebelumnya is None or tanggal > sebelumnya["tanggal"]:
            laporan_terbaru[kode_aset] = {
                "tanggal": tanggal,
                "laporan": item
            }

    for item in aset:
        kode_aset = item.get("kode_aset")
        terbaru = laporan_terbaru.get(kode_aset)

        if not terbaru:
            continue

        tanggal_laporan = terbaru["tanggal"]
        tanggal_update = item.get("tgl_update")

        if isinstance(tanggal_update, datetime):
            tanggal_update = tanggal_update.date()

        if isinstance(tanggal_update, str):
            tanggal_update = date.fromisoformat(tanggal_update)

        if tanggal_update is None or tanggal_laporan >= tanggal_update:
            item["kondisi"] = terbaru["laporan"]["kondisi"]
            item["sumber_kondisi"] = "laporan_penelusuran"
            item["tanggal_kondisi"] = tanggal_laporan
        else:
            item["sumber_kondisi"] = "data_aset"
            item["tanggal_kondisi"] = tanggal_update

    # 5. Proses petak tersier
    hasil_petak = proses_petak_tersier(petak)
    petak_bersih = hasil_petak["data"]

    # 6. Hubungkan petak ke bangunan sadap
    hubungan_petak = hubungkan_petak_ke_sadap(
        petak_bersih,
        aset
    )

    # 7. Tambahkan luas petak ke data hubungan
    peta_luas = {
        p["kode_petak"]: p["luas_geometri_ha"]
        for p in petak_bersih
    }

    for hubungan in hubungan_petak:
        hubungan["luas_geometri_ha"] = peta_luas.get(
            hubungan["kode_petak"]
        )

    # 8. Hitung dampak kerusakan
    dampak = hitung_dampak_bangunan(
        aset,
        hubungan_petak,
        arah_ruas
    )

    # 9. Hitung prioritas rehabilitasi
    prioritas = hitung_prioritas_rehabilitasi(dampak)

    return {
        "aset": aset,
        "laporan": laporan_terhubung,
        "saluran": saluran,
        "petak": petak_bersih,
        "hubungan_petak": hubungan_petak,
        "arah_ruas": arah_ruas,
        "dampak": dampak,
        "prioritas": prioritas,
        "duplikat_saluran": duplikat_saluran
        
    }
