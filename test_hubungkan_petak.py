from cleaning import bersihkan_aset, bersihkan_saluran, bersihkan_petak
from geospatial import (
    deduplikasi_saluran,
    hubungkan_bangunan_ke_saluran,
    bangun_graph_titik_sambungan,
    tentukan_arus_dari_bendung,
    proses_petak_tersier,
    hubungkan_petak_ke_sadap
)

# Baca data
aset = bersihkan_aset("data/aset_bangunan.csv")
saluran = bersihkan_saluran("data/saluran.geojson")
petak = bersihkan_petak("data/petak_tersier.geojson")

# Bersihkan saluran duplikat
saluran_unik, _ = deduplikasi_saluran(saluran)

# Bangun jaringan
graph, peta_ujung = bangun_graph_titik_sambungan(saluran_unik)

titik_bendung = peta_ujung[("KW-R01", 1)]

arah_ruas = tentukan_arus_dari_bendung(
    graph,
    titik_bendung,
    peta_ujung
)

# Hubungkan bangunan ke saluran
hasil_aset = hubungkan_bangunan_ke_saluran(
    aset,
    saluran_unik,
    arah_ruas
)

# Proses petak
hasil_proses = proses_petak_tersier(petak)

# Hubungkan petak dengan bangunan sadap
hasil = hubungkan_petak_ke_sadap(
    hasil_proses["data"],
    hasil_aset
)

print("\n=== HASIL HUBUNGAN PETAK DAN SADAP ===")

for item in hasil:
    print(
        item["kode_petak"],
        "| Sadap:", item["kode_aset_sadap"],
        "| Metode:", item["metode_pencocokan"],
        "| Status:", item["status_sadap"]
    )

print("\nTotal petak:", len(hasil))
print("Terhubung:", sum(x["status_sadap"] == "terhubung" for x in hasil))
print("Tanpa sadap:", sum(x["status_sadap"] == "tanpa_sadap" for x in hasil))
