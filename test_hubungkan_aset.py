from cleaning import bersihkan_aset, bersihkan_saluran
from geospatial import (
    deduplikasi_saluran,
    deduplikasi_aset,
    hubungkan_bangunan_ke_saluran,
    bangun_graph_titik_sambungan,
    tentukan_arus_dari_bendung
)
from collections import Counter

# Baca data
daftar_aset = bersihkan_aset("data/aset_bangunan.csv")
saluran = bersihkan_saluran("data/saluran.geojson")

# Hilangkan saluran duplikat
saluran_unik, duplikat = deduplikasi_saluran(saluran)

# Bangun jaringan berdasarkan titik sambungan
graph, peta_ujung = bangun_graph_titik_sambungan(saluran_unik)

# Titik bendung berada di ujung kedua KW-R01
titik_bendung = peta_ujung[("KW-R01", 1)]

# Tentukan arah aliran dari bendung
arah_ruas = tentukan_arus_dari_bendung(
    graph,
    titik_bendung,
    peta_ujung
)

# Hubungkan bangunan dengan saluran dan hitung posisi dari hulu
hasil = hubungkan_bangunan_ke_saluran(
    daftar_aset,
    saluran_unik,
    arah_ruas
)

# Tampilkan ringkasan
print("\n=== HASIL HUBUNGAN BANGUNAN DAN SALURAN ===")
print("Total bangunan:", len(hasil))

dekat = sum(
    1 for a in hasil
    if a["status_kedekatan"] == "dekat_saluran"
)

jauh = sum(
    1 for a in hasil
    if a["status_kedekatan"] == "jauh_dari_saluran"
)

tidak_valid = sum(
    1 for a in hasil
    if a["status_kedekatan"] == "koordinat_tidak_valid"
)

print("Dekat saluran (<=50 m):", dekat)
print("Jauh dari saluran (>50 m):", jauh)
print("Koordinat tidak valid:", tidak_valid)

print("\n=== CONTOH HASIL ===")

for aset in hasil[:10]:
    print(
        aset["kode_aset"],
        "|", aset["jenis"],
        "|", aset["saluran_terdekat"],
        "| Ruas:", aset["id_ruas_terdekat"],
        "|", aset["jarak_saluran_meter"], "meter",
        "| Posisi:", aset["posisi_hulu_meter"], "meter",
        "|", aset["status_kedekatan"]
    )

print("\n=== BANGUNAN DI LUAR BATAS 50 METER ===")

for aset in hasil:
    if aset["status_kedekatan"] != "dekat_saluran":
        print(
            aset["kode_aset"],
            "|", aset["jenis"],
            "| Jarak:", aset["jarak_saluran_meter"],
            "| Status:", aset["status_kedekatan"]
        )

print("\n=== BANGUNAN BAGI DAN SADAP ===")

for aset in hasil:
    if aset["jenis"] in [
        "bangunan bagi",
        "bangunan bagi-sadap",
        "bangunan sadap",
        "bendung"
    ]:
        if aset["status_kedekatan"] == "dekat_saluran":
            print(
                aset["kode_aset"],
                "|", aset["jenis"],
                "|", aset["saluran_terdekat"],
                "|", aset["jarak_saluran_meter"], "meter"
            )


print("\n=== PEMERIKSAAN DUPLIKAT KODE ASET ===")

jumlah_kode = Counter(
    a["kode_aset"] for a in hasil
)

kode_duplikat = [
    kode for kode, jumlah in jumlah_kode.items()
    if jumlah > 1
]

for kode in kode_duplikat:
    print(f"\nKode aset: {kode}")

    for a in hasil:
        if a["kode_aset"] == kode:
            print(
                "Jenis:", a["jenis"],
                "| Saluran:", a["nama_saluran"],
                "| X:", a["x"],
                "| Y:", a["y"],
                "| Kondisi:", a["kondisi"],
                "| Tanggal update:", a["tgl_update"]
            )

print("\n=== UJI DEDUPLIKASI ASET ===")

aset_unik, aset_duplikat = deduplikasi_aset(daftar_aset)

print("Total data awal:", len(daftar_aset))
print("Total aset unik:", len(aset_unik))
print("Total kode aset duplikat:", len(aset_duplikat))

for item in aset_duplikat:
    dipertahankan = item["dipertahankan"]

    print(
        item["kode_aset"],
        "| Data:", item["jumlah_data"],
        "| Kondisi:", dipertahankan["kondisi"],
        "| Tanggal:", dipertahankan["tgl_update"]
    )