from cleaning import bersihkan_aset, bersihkan_saluran, bersihkan_petak
from geospatial import (
    deduplikasi_saluran,
    hubungkan_bangunan_ke_saluran,
    bangun_graph_titik_sambungan,
    tentukan_arus_dari_bendung,
    proses_petak_tersier,
    hubungkan_petak_ke_sadap,
    hitung_dampak_bangunan,
    hitung_prioritas_rehabilitasi
)

aset = bersihkan_aset("data/aset_bangunan.csv")
saluran = bersihkan_saluran("data/saluran.geojson")
petak = bersihkan_petak("data/petak_tersier.geojson")

saluran, _ = deduplikasi_saluran(saluran)

graph, peta_ujung = bangun_graph_titik_sambungan(saluran)

arah = tentukan_arus_dari_bendung(
    graph,
    peta_ujung[("KW-R01", 1)],
    peta_ujung
)

aset = hubungkan_bangunan_ke_saluran(
    aset, saluran, arah
)

hasil_petak = proses_petak_tersier(petak)

hubungan = hubungkan_petak_ke_sadap(
    hasil_petak["data"], aset
)

# Gabungkan luas petak dengan hasil hubungan sadap
luas_petak = {
    p["kode_petak"]: p["luas_geometri_ha"]
    for p in hasil_petak["data"]
}

for p in hubungan:
    p["luas_geometri_ha"] = luas_petak.get(
        p["kode_petak"]
    )

dampak = hitung_dampak_bangunan(
    aset, hubungan, arah
)

print("\n=== HASIL PERHITUNGAN DAMPAK ===")

for item in dampak:
    print(
        item["kode_aset"],
        "|", item["kondisi"],
        "| Petak terdampak:", item["jumlah_petak_terdampak"],
        "| Luas:", item["luas_terdampak_ha"], "ha"
    )

print("\nTotal bangunan dihitung:", len(dampak))

prioritas = hitung_prioritas_rehabilitasi(dampak)

print("\n=== PRIORITAS REHABILITASI ===")

for item in prioritas:
    print(
        item["kode_aset"],
        "|", item["kondisi"],
        "| Luas:", item["luas_terdampak_ha"], "ha",
        "| Skor:", item["skor_prioritas"]
    )

print("\nTotal bangunan prioritas:", len(prioritas))
