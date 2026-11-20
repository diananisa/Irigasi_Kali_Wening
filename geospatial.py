# geospatial.py

from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union, nearest_points
from pyproj import Transformer

from cleaning import normalisasi_angka, bersihkan_saluran, normalisasi_teks
import math
import json
import networkx as nx

# TRANSFORMASI KOORDINAT UTM 49S KE WGS84
transformer_utm_to_wgs84 = Transformer.from_crs(
    "EPSG:32749",
    "EPSG:4326",
    always_xy=True
)

# TRANSFORMASI WGS84 KE UTM 49S
transformer_wgs84_to_utm = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32749",
    always_xy=True
)

# NORMALISASI KOORDINAT

def normalisasi_koordinat(x, y):
    """
    Mendeteksi jenis koordinat dan mengubahnya menjadi WGS84.
    Hasil: longitude, latitude, status
    """

    if x is None or y is None:
        return None, None, "koordinat_kosong"

    try:
        x = float(x)
        y = float(y)
    except (ValueError, TypeError):
        return None, None, "koordinat_tidak_valid"

    # Koordinat nol dianggap tidak valid
    if x == 0 or y == 0:
        return None, None, "koordinat_tidak_valid"

    # 1. DETEKSI WGS84 NORMAL
    if -180 <= x <= 180 and -90 <= y <= 90:
        return x, y, "wgs84"

    # 2. DETEKSI LATITUDE DAN LONGITUDE TERTUKAR
    if -90 <= x <= 90 and -180 <= y <= 180:
        return y, x, "koordinat_tertukar"

    # 3. DETEKSI UTM (EASTING DAN NORTHING)
    easting = None
    northing = None

    # UTM normal: X = Easting, Y = Northing
    if 100000 <= x <= 900000 and 0 <= y <= 10000000:
        easting = x
        northing = y

    # UTM tertukar: X = Northing, Y = Easting
    elif 100000 <= y <= 900000 and 0 <= x <= 10000000:
        easting = y
        northing = x

    if easting is not None:
        lon, lat = transformer_utm_to_wgs84.transform(
            easting, northing
        )

        # Validasi hasil transformasi
        if -180 <= lon <= 180 and -90 <= lat <= 90:
            return lon, lat, "utm_dikonversi"

    # 4. KOORDINAT DI LUAR JANGKAUAN
    return None, None, "koordinat_tidak_valid"

# NORMALISASI GEOMETRI GEOJSON

def normalisasi_geometri(geometry):
    """
    Mengubah geometri GeoJSON menjadi WGS84.
    Menangani koordinat normal, terbalik, dan UTM.
    """

    if geometry is None:
        return None, "geometri_kosong"

    try:
        geom = shape(geometry)

        if geom.is_empty:
            return None, "geometri_kosong"

        titik = geom.representative_point()
        x, y = titik.x, titik.y

        # WGS84 normal: longitude, latitude
        if -180 <= x <= 180 and -90 <= y <= 90:
            return geom, "wgs84"

        # WGS84 terbalik: latitude, longitude
        if -90 <= x <= 90 and 90 <= y <= 180:
            geom = transform(
                lambda x, y: (y, x),
                geom
            )
            return geom, "wgs84_dibalik"

        # UTM
        if 100000 <= x <= 900000 and 0 <= y <= 10000000:
            geom_wgs84 = transform(
                transformer_utm_to_wgs84.transform,
                geom
            )
            return geom_wgs84, "utm_dikonversi"

        return None, "geometri_tidak_valid"

    except Exception:
        return None, "geometri_tidak_valid"

# VALIDASI DAN PERBAIKAN GEOMETRI

def perbaiki_geometri(geom):
    """
    Memeriksa validitas geometri.
    Memperbaiki Polygon yang tidak valid.
    """

    if geom is None:
        return None, "geometri_kosong"

    if geom.is_empty:
        return None, "geometri_kosong"

    if geom.is_valid:
        return geom, "valid"

    # Perbaikan geometri Polygon
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        hasil = geom.buffer(0)

        if not hasil.is_empty and hasil.is_valid:
            return hasil, "diperbaiki"

    return None, "geometri_tidak_valid"

# PERHITUNGAN PANJANG SALURAN

def hitung_panjang_saluran(geom):
    """
    Menghitung panjang geometri saluran dalam meter.
    Geometri dikonversi ke UTM 49S terlebih dahulu.
    """

    if geom is None or geom.is_empty:
        return 0.0

    geom_utm = transform(
        transformer_wgs84_to_utm.transform,
        geom
    )

    return geom_utm.length

# PERHITUNGAN LUAS PETAK TERSIER

def hitung_luas_petak(geom):
    """
    Menghitung luas polygon dalam hektare (ha).
    Geometri dikonversi ke UTM 49S terlebih dahulu.
    """

    if geom is None or geom.is_empty:
        return 0.0

    geom_utm = transform(
        transformer_wgs84_to_utm.transform,
        geom
    )

    luas_m2 = geom_utm.area
    luas_ha = luas_m2 / 10000

    return luas_ha

def deduplikasi_petak(daftar_petak):
    petak_unik = {}
    duplikat = []

    for petak in daftar_petak:
        properties = petak.get("properties", petak)
        kode = properties.get("kode_petak")

        if not kode:
            continue

        if kode not in petak_unik:
            petak_unik[kode] = petak
        else:
            duplikat.append(kode)

    return list(petak_unik.values()), duplikat

def kelompokkan_saluran(daftar_saluran):
    kelompok = {}

    for saluran in daftar_saluran:
        nama = saluran.get("nama_saluran", "TIDAK DIKETAHUI")

        if nama not in kelompok:
            kelompok[nama] = []

        kelompok[nama].append(saluran)

    return kelompok

def deteksi_koneksi_ruas(geom_a, geom_b, toleransi=10):
    """
    Memeriksa apakah titik ujung dua ruas saluran
    terhubung dalam toleransi meter.
    """
    geom_a_utm = transform(
        transformer_wgs84_to_utm.transform,
        geom_a
    )

    geom_b_utm = transform(
        transformer_wgs84_to_utm.transform,
        geom_b
    )

    ujung_a = [
        Point(geom_a_utm.coords[0]),
        Point(geom_a_utm.coords[-1])
    ]

    ujung_b = [
        Point(geom_b_utm.coords[0]),
        Point(geom_b_utm.coords[-1])
    ]

    koneksi = []

    for i, titik_a in enumerate(ujung_a):
        for j, titik_b in enumerate(ujung_b):
            jarak = titik_a.distance(titik_b)

            if jarak <= toleransi:
                koneksi.append({
                    "ujung_a": i,
                    "ujung_b": j,
                    "jarak_meter": round(jarak, 2)
                })

    return koneksi

def bangun_graph_saluran(ruas_saluran, toleransi=10):
    graph = nx.Graph()

    for ruas in ruas_saluran:
        graph.add_node(
            ruas["id_ruas"],
            nama_saluran=ruas["nama_saluran"],
            tingkat=ruas["tingkat"],
            kondisi=ruas["kondisi"]
        )

    for i in range(len(ruas_saluran)):
        for j in range(i + 1, len(ruas_saluran)):
            ruas_a = ruas_saluran[i]
            ruas_b = ruas_saluran[j]

            koneksi = deteksi_koneksi_ruas(
                ruas_a["geometry"],
                ruas_b["geometry"],
                toleransi
            )

            if koneksi:
                graph.add_edge(
                    ruas_a["id_ruas"],
                    ruas_b["id_ruas"],
                    koneksi=koneksi
                )

    return graph

def bangun_graph_titik_sambungan(ruas_saluran, toleransi=10):
    """
    Membentuk jaringan berdasarkan titik sambungan fisik
    pada kedua ujung setiap ruas saluran.
    """

    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:32749",
        always_xy=True
    )

    graph_ujung = nx.Graph()
    data_ruas = []

    # 1. Siapkan kedua ujung setiap ruas dalam koordinat UTM
    for ruas in ruas_saluran:
        geom = ruas["geometry"]

        if isinstance(geom, dict):
            geom = shape(geom)

        geom, status = normalisasi_geometri(geom)
        geom, status_perbaikan = perbaiki_geometri(geom)

        if geom is None or geom.is_empty:
            continue

        geom_utm = transform(
            transformer.transform,
            geom
        )

        if geom_utm.geom_type != "LineString":
            continue

        koordinat = list(geom_utm.coords)

        ujung_awal = Point(koordinat[0])
        ujung_akhir = Point(koordinat[-1])

        id_ruas = ruas["id_ruas"]

        id_awal = (id_ruas, 0)
        id_akhir = (id_ruas, 1)

        graph_ujung.add_node(
            id_awal,
            titik=ujung_awal
        )

        graph_ujung.add_node(
            id_akhir,
            titik=ujung_akhir
        )

        data_ruas.append({
            "id_ruas": id_ruas,
            "nama_saluran": ruas["nama_saluran"],
            "tingkat": ruas["tingkat"],
            "kondisi": ruas["kondisi"],
            "geometry": geom_utm,
            "ujung_awal": id_awal,
            "ujung_akhir": id_akhir
        })

    # 2. Hubungkan ujung-ujung yang berjarak maksimal 10 meter
    daftar_ujung = list(graph_ujung.nodes(data=True))

    for i in range(len(daftar_ujung)):
        id_a, data_a = daftar_ujung[i]

        for j in range(i + 1, len(daftar_ujung)):
            id_b, data_b = daftar_ujung[j]

            # Jangan menghubungkan dua ujung dari ruas yang sama
            if id_a[0] == id_b[0]:
                continue

            jarak = data_a["titik"].distance(
                data_b["titik"]
            )

            if jarak <= toleransi:
                graph_ujung.add_edge(
                    id_a,
                    id_b,
                    jarak_meter=jarak
                )

    # 3. Kelompokkan ujung yang saling terhubung
    kelompok = list(nx.connected_components(graph_ujung))

    peta_ujung = {}

    for nomor, anggota in enumerate(kelompok, start=1):
        id_sambungan = f"S{nomor:03d}"

        for id_ujung in anggota:
            peta_ujung[id_ujung] = id_sambungan

    # 4. Bentuk graph ruas berdasarkan titik sambungan
    graph = nx.MultiGraph()

    for ruas in data_ruas:
        node_awal = peta_ujung[ruas["ujung_awal"]]
        node_akhir = peta_ujung[ruas["ujung_akhir"]]

        graph.add_edge(
            node_awal,
            node_akhir,
            key=ruas["id_ruas"],
            id_ruas=ruas["id_ruas"],
            nama_saluran=ruas["nama_saluran"],
            tingkat=ruas["tingkat"],
            kondisi=ruas["kondisi"],
            panjang_meter=ruas["geometry"].length,
            geometry=ruas["geometry"]
        )

    return graph, peta_ujung

def tentukan_arus_dari_bendung(graph, titik_awal, peta_ujung):
    """
    Menentukan arah hulu dan hilir setiap ruas
    berdasarkan penelusuran dari titik bendung.
    """

    if titik_awal not in graph:
        raise ValueError("Titik awal bendung tidak ditemukan.")

    if not nx.is_tree(graph):
        raise ValueError(
            "Jaringan bukan pohon. Arah aliran perlu diperiksa."
        )

    hasil = []

    for hulu, hilir in nx.bfs_edges(
        graph,
        source=titik_awal
    ):
        data_ruas = graph.get_edge_data(hulu, hilir)

        for id_ruas, data in data_ruas.items():
            if peta_ujung[(id_ruas, 0)] == hulu:
                arah_geometri = "maju"
            else:
                arah_geometri = "terbalik"
            hasil.append({
                "id_ruas": id_ruas,
                "arah_geometri": arah_geometri,
                "titik_hulu": hulu,
                "titik_hilir": hilir,
                "nama_saluran": data["nama_saluran"],
                "tingkat": data["tingkat"],
                "kondisi": data["kondisi"],
                "panjang_meter": data["panjang_meter"],
                "geometry": data["geometry"]
            })

    return hasil

def telusuri_jaringan(graph, ruas_awal):
    dikunjungi = set()
    urutan = []

    def kunjungi(ruas):
        if ruas in dikunjungi:
            return

        dikunjungi.add(ruas)
        urutan.append(ruas)

        for tetangga in sorted(graph.neighbors(ruas)):
            if tetangga not in dikunjungi:
                kunjungi(tetangga)

    if ruas_awal not in graph:
        return []

    kunjungi(ruas_awal)

    return urutan

def deteksi_duplikat_geometri_saluran(daftar_saluran):
    duplikat = []

    ruas_valid = []

    for saluran in daftar_saluran:
        geom, status = normalisasi_geometri(
            saluran.get("geometry")
        )

        geom, status_validasi = perbaiki_geometri(geom)

        if geom is not None:
            ruas_valid.append({
                "id_ruas": saluran["id_ruas"],
                "nama_saluran": saluran["nama_saluran"],
                "geometry": geom
            })

    for i in range(len(ruas_valid)):
        for j in range(i + 1, len(ruas_valid)):
            geom_a = ruas_valid[i]["geometry"]
            geom_b = ruas_valid[j]["geometry"]

            if geom_a.equals(geom_b):
                duplikat.append({
                    "id_ruas_a": ruas_valid[i]["id_ruas"],
                    "id_ruas_b": ruas_valid[j]["id_ruas"],
                    "nama_a": ruas_valid[i]["nama_saluran"],
                    "nama_b": ruas_valid[j]["nama_saluran"]
                })

    return duplikat

def deduplikasi_saluran(daftar_saluran):
    ruas_unik = []
    duplikat = []

    for saluran in daftar_saluran:
        geom, status = normalisasi_geometri(
            saluran.get("geometry")
        )

        geom, status_validasi = perbaiki_geometri(geom)

        if geom is None:
            continue

        ditemukan = False

        for ruas in ruas_unik:
            if ruas["geometry"].equals(geom):
                duplikat.append({
                    "id_ruas": saluran["id_ruas"],
                    "nama_saluran": saluran["nama_saluran"],
                    "duplikat_dari": ruas["id_ruas"],
                    "alasan": "geometri_identik"
                })

                ditemukan = True
                break

        if not ditemukan:
            ruas_unik.append({
                "id_ruas": saluran["id_ruas"],
                "nama_saluran": saluran["nama_saluran"],
                "tingkat": saluran["tingkat"],
                "kondisi": saluran["kondisi"],
                "geometry": geom
            })

    return ruas_unik, duplikat

def gabungkan_geometri_saluran(daftar_saluran):
    kelompok = kelompokkan_saluran(daftar_saluran)
    hasil = {}

    for nama, ruas in kelompok.items():
        geometri = []

        for saluran in ruas:
            geom, status = normalisasi_geometri(
                saluran.get("geometry")
            )

            geom, status_validasi = perbaiki_geometri(geom)

            if geom is not None:
                geometri.append(geom)

        if geometri:
            gabungan = unary_union(geometri)

            hasil[nama] = {
                "geometry": gabungan,
                "jumlah_ruas": len(geometri)
            }

    return hasil

def deduplikasi_aset(daftar_aset):
    kelompok = {}

    for aset in daftar_aset:
        kode = aset.get("kode_aset")

        if not kode:
            continue

        if kode not in kelompok:
            kelompok[kode] = []
        
        kelompok[kode].append(aset)

    aset_unik = []
    duplikat = []

    for kode, daftar in kelompok.items():
        daftar_urut = sorted(
            daftar,
            key=lambda a: a.get("tgl_update") or __import__("datetime").date.min,
            reverse=True
        )

        aset_unik.append(daftar_urut[0])

        if len(daftar) > 1:
            duplikat.append({
                "kode_aset": kode,
                "jumlah_data": len(daftar),
                "dipertahankan": daftar_urut[0],
                "jumlah_dihapus": len(daftar) - 1
            })

    return aset_unik, duplikat

def hubungkan_bangunan_ke_saluran(daftar_aset, daftar_saluran, arah_ruas=None):
    daftar_aset, _ = deduplikasi_aset(daftar_aset)
    print("DEBUG - Aset setelah deduplikasi:", len(daftar_aset))
    hasil = []

    peta_arus = {}

    if arah_ruas:
        peta_arus = {
            ruas["id_ruas"]: ruas["arah_geometri"]
            for ruas in arah_ruas
        }

    ruas_valid = []

    # Siapkan geometri saluran dalam UTM
    for saluran in daftar_saluran:
        geom = saluran.get("geometry")

        if isinstance(geom, dict):
            geom = shape(geom)

        geom, status = normalisasi_geometri(geom)

        if geom is None:
            continue

        geom, status_perbaikan = perbaiki_geometri(geom)

        if geom is None or geom.is_empty:
            continue

        geom_utm = transform(
            transformer_wgs84_to_utm.transform,
            geom
        )

        id_ruas = saluran.get("id_ruas")

        ruas_valid.append({
            "id_ruas": id_ruas,
            "nama_saluran": saluran.get("nama_saluran"),
            "geometry": geom_utm,
            "panjang_meter": geom_utm.length,
            "arah_geometri": peta_arus.get(id_ruas)
        })

    # Periksa setiap bangunan
    for aset in daftar_aset:
        lon, lat, status_koordinat = normalisasi_koordinat(
            aset.get("x"),
            aset.get("y")
        )

        if lon is None or lat is None:
            hasil.append({
                **aset,
                "x": None,
                "y": None,
                "id_ruas_terdekat": None,
                "posisi_geometri_meter": None,
                "posisi_hulu_meter": None,
                "saluran_terdekat": None,
                "jarak_saluran_meter": None,
                "status_kedekatan": "koordinat_tidak_valid",
                "status_koordinat": status_koordinat
            })
            continue

        titik = Point(lon, lat)

        titik_utm = transform(
            transformer_wgs84_to_utm.transform,
            titik
        )
        posisi_ruas = None
        terdekat = None
        jarak_minimum = float("inf")

        for ruas in ruas_valid:
            jarak = titik_utm.distance(ruas["geometry"])

            if jarak < jarak_minimum:
                jarak_minimum = jarak
                terdekat = ruas

        if terdekat is None:
            status = "saluran_tidak_ditemukan"
        elif jarak_minimum > 2000:
            status = "koordinat_tidak_valid"
        elif jarak_minimum > 50:
            status = "jauh_dari_saluran"
        else:
            status = "dekat_saluran"
            
        posisi_hulu = None

        if terdekat is not None:
            posisi_geometri = terdekat["geometry"].project(titik_utm)

            if terdekat["arah_geometri"] == "terbalik":
                posisi_hulu = (
                    terdekat["panjang_meter"] - posisi_geometri
                )
            else:
                posisi_hulu = posisi_geometri

            posisi_hulu = round(posisi_hulu, 2)

        hasil.append({
            **aset,
            "x": round(lon, 8),
            "y": round(lat, 8),
            "id_ruas_terdekat": (
                terdekat["id_ruas"] if terdekat else None
            ),
            "posisi_geometri_meter": (
                round(posisi_geometri, 2)
                if terdekat else None
            ),
            "posisi_hulu_meter": posisi_hulu,
            "posisi_ruas_meter": posisi_ruas,
            "saluran_terdekat": (
                terdekat["nama_saluran"] if terdekat else None
            ),
            "jarak_saluran_meter": (
                round(jarak_minimum, 2)
                if terdekat else None
            ),
            "status_kedekatan": status,
            "status_koordinat": status_koordinat
        })

    return hasil

def proses_petak_tersier(daftar_petak):
    petak_unik, duplikat = deduplikasi_petak(daftar_petak)

    hasil = []
    total_luas = 0
    jumlah_anomali = 0
    geometri_gagal = []

    for feature in petak_unik:
        if "properties" in feature:
            properties = feature.get("properties", {})
        else:
            properties = feature

        geom, status = normalisasi_geometri(
            feature.get("geometry")
        )

        geom, status_validasi = perbaiki_geometri(geom)

        kode = properties.get("kode_petak")

        if geom is None:
            geometri_gagal.append(kode)
            continue

        luas_ha = hitung_luas_petak(geom)

        luas_baku = normalisasi_angka(
            properties.get(
                "luas_baku",
                properties.get("luas_bak")
            )
        )

        if luas_baku is not None and luas_baku > 1000:
            luas_baku = luas_baku / 10000

        selisih = None

        if luas_baku is not None and luas_baku > 0:
            selisih = abs(
                (luas_ha - luas_baku) / luas_baku
            ) * 100

        anomali = (
            selisih is not None
            and selisih > 20
        )

        if anomali:
            jumlah_anomali += 1

        luas_dampak = (
            luas_ha if anomali or luas_baku is None else luas_baku
        )

        hasil.append({
            "kode_petak": kode,
            "nomenklatur_sadap": normalisasi_teks(properties.get("nomenklatur_sadap")),
            "luas_geometri_ha": round(luas_ha, 2),
            "luas_baku_ha": round(luas_baku, 2)
                if luas_baku is not None else None,
            "luas_dampak_ha": round(luas_dampak, 2),
            "selisih_persen": round(selisih, 2)
                if selisih is not None else None,
            "anomali": anomali,
            "geometry": geom,
            "status_geometri": status,
            "status_validasi": status_validasi
        })

        total_luas += luas_ha

    return {
        "data": hasil,
        "total_awal": len(daftar_petak),
        "total_unik": len(petak_unik),
        "duplikat": duplikat,
        "jumlah_berhasil": len(hasil),
        "geometri_gagal": geometri_gagal,
        "total_luas_ha": round(total_luas, 2),
        "jumlah_anomali": jumlah_anomali
    }

def hubungkan_petak_ke_sadap(daftar_petak, daftar_aset, jarak_maksimal=200):
    daftar_aset, _ = deduplikasi_aset(daftar_aset)

    aset_sadap = [
        aset for aset in daftar_aset
        if aset.get("jenis") in (
            "bangunan_sadap",
            "bangunan_bagi_sadap",
            "bangunan sadap",
            "bangunan bagi-sadap"
        )
        and aset.get("status_kedekatan") == "dekat_saluran"
    ]

    aset_nomenklatur = {}

    for aset in aset_sadap:
        nomenklatur = normalisasi_teks(aset.get("nomenklatur"))

        if nomenklatur:
            aset_nomenklatur.setdefault(nomenklatur, []).append(aset)

    hasil = []

    for petak in daftar_petak:
        nomenklatur = normalisasi_teks(
            petak.get("nomenklatur_sadap")
        )

        geom, _ = normalisasi_geometri(petak.get("geometry"))

        batas_petak = None

        if geom is not None:
            geom_utm = transform(
                transformer_wgs84_to_utm.transform,
                geom
            )
            batas_petak = geom_utm.boundary

        bangunan = None
        metode = None
        jarak = None

        kandidat = aset_nomenklatur.get(nomenklatur, [])

        # Pencocokan nomenklatur yang tidak ambigu
        if len(kandidat) == 1:
            bangunan = kandidat[0]
            metode = "nomenklatur"

        else:
            # Jika tidak cocok atau ambigu, cari sadap terdekat
            jarak_terdekat = float("inf")

            if batas_petak is not None:
                for aset in aset_sadap:
                    lon, lat, _ = normalisasi_koordinat(
                        aset.get("x"),
                        aset.get("y")
                    )

                    if lon is None or lat is None:
                        continue

                    titik = transform(
                        transformer_wgs84_to_utm.transform,
                        Point(lon, lat)
                    )

                    jarak_sekarang = batas_petak.distance(titik)

                    if jarak_sekarang < jarak_terdekat:
                        jarak_terdekat = jarak_sekarang
                        bangunan = aset

                if bangunan and jarak_terdekat <= jarak_maksimal:
                    metode = "jarak_terdekat"
                    jarak = round(jarak_terdekat, 2)
                else:
                    bangunan = None

        hasil.append({
            "kode_petak": petak.get("kode_petak"),
            "kode_aset_sadap": (
                bangunan.get("kode_aset") if bangunan else None
            ),
            "nomenklatur_sadap": nomenklatur,
            "metode_pencocokan": metode,
            "jarak_meter": jarak,
            "status_sadap": (
                "terhubung" if bangunan else "tanpa_sadap"
            )
        })

    return hasil

def hitung_dampak_bangunan(daftar_aset, daftar_petak, arah_ruas):
    """
    Menghitung luas petak tersier di hilir setiap bangunan.
    Bangunan dengan kondisi baik tetap dihitung, tetapi tidak
    masuk prioritas rehabilitasi karena bobot kondisinya nol.
    """

    hasil = []

    peta_arus = {
        ruas["id_ruas"]: ruas
        for ruas in arah_ruas
    }

    peta_aset = {
        aset["kode_aset"]: aset
        for aset in daftar_aset
    }

    peta_petak = {
        petak["kode_petak"]: petak
        for petak in daftar_petak
    }

    # Graph terarah mengikuti aliran dari hulu ke hilir.
    graph_hilir = nx.DiGraph()

    for ruas in arah_ruas:
        graph_hilir.add_edge(
            ruas["titik_hulu"],
            ruas["titik_hilir"]
        )

    for aset in daftar_aset:
        kode_aset = aset.get("kode_aset")
        id_ruas = aset.get("id_ruas_terdekat")
        posisi = aset.get("posisi_hulu_meter")
        status = aset.get("status_kedekatan")

        petak_terdampak = []

        # Bangunan yang tidak memiliki posisi valid
        # tidak dapat dihitung dampaknya.
        if (
            status != "dekat_saluran"
            or id_ruas not in peta_arus
            or posisi is None
        ):
            hasil.append({
                "kode_aset": kode_aset,
                "kondisi": aset.get("kondisi"),
                "id_ruas": id_ruas,
                "jumlah_petak_terdampak": 0,
                "luas_terdampak_ha": 0,
                "petak_terdampak": [],
                "status_dampak": status
            })
            continue

        ruas_awal = peta_arus[id_ruas]
        titik_hilir = ruas_awal["titik_hilir"]

        # Semua titik yang dapat dicapai dari posisi hilir.
        titik_hilir_berikutnya = {titik_hilir} | nx.descendants(
            graph_hilir,
            titik_hilir
        )

        for hubungan in daftar_petak:

            if hubungan.get("status_sadap") != "terhubung":
                continue

            kode_sadap = hubungan.get("kode_aset_sadap")
            sadap = peta_aset.get(kode_sadap)

            if sadap is None:
                continue

            if sadap.get("status_kedekatan") != "dekat_saluran":
                continue

            ruas_sadap_id = sadap.get("id_ruas_terdekat")

            if ruas_sadap_id not in peta_arus:
                continue

            ruas_sadap = peta_arus[ruas_sadap_id]

            # Jika bangunan rusak adalah bangunan sadap itu sendiri,
            # petak yang dilayani tetap dianggap terdampak.
            if kode_sadap == kode_aset:
                di_hilir = True

            elif ruas_sadap_id == id_ruas:
                posisi_sadap = sadap.get("posisi_hulu_meter")

                di_hilir = (
                    posisi_sadap is not None
                    and posisi_sadap >= posisi
                )

            else:
                di_hilir = (
                    ruas_sadap["titik_hulu"]
                    in titik_hilir_berikutnya
                )

            if not di_hilir:
                continue

            kode_petak = hubungan.get("kode_petak")
            data_petak = peta_petak.get(kode_petak)

            if data_petak is None:
                continue

            luas = data_petak.get(
                "luas_dampak_ha",
                data_petak.get("luas_geometri_ha")
            )

            if luas is None:
                continue

            petak_terdampak.append({
                "kode_petak": kode_petak,
                "luas_ha": luas
            })

        total_luas = round(
            sum(p["luas_ha"] for p in petak_terdampak),
            2
        )

        hasil.append({
            "kode_aset": kode_aset,
            "kondisi": aset.get("kondisi"),
            "id_ruas": id_ruas,
            "jumlah_petak_terdampak": len(petak_terdampak),
            "luas_terdampak_ha": total_luas,
            "petak_terdampak": petak_terdampak,
            "status_dampak": "dihitung"
        })

    return hasil

def hitung_prioritas_rehabilitasi(daftar_dampak):
    """
    Menghitung dan mengurutkan prioritas rehabilitasi
    berdasarkan kondisi bangunan dan luas petak terdampak.
    """

    bobot_kondisi = {
        "baik": 0,
        "rusak_ringan": 1,
        "rusak_sedang": 2,
        "rusak_berat": 4,
        # Kompatibilitas data lama
        "rusak ringan": 1,
        "rusak sedang": 2,
        "rusak berat": 4
    }

    hasil = []

    for dampak in daftar_dampak:
        kondisi = dampak.get("kondisi")
        luas = dampak.get("luas_terdampak_ha", 0)

        bobot = bobot_kondisi.get(kondisi, 0)
        skor = round(bobot * luas, 2)

        if skor <= 0:
            continue

        hasil.append({
            "kode_aset": dampak["kode_aset"],
            "kondisi": kondisi,
            "id_ruas": dampak.get("id_ruas"),
            "bobot_kondisi": bobot,
            "luas_terdampak_ha": luas,
            "skor_prioritas": skor
        })

    hasil.sort(
        key=lambda item: (
            -item["skor_prioritas"],
            item["kode_aset"]
        )
    )

    return hasil

def hubungkan_laporan_ke_aset(
    daftar_laporan,
    daftar_aset,
    jarak_maksimal=30
):
    hasil = []

    peta_nomenklatur = {}

    for aset in daftar_aset:
        nomenklatur = normalisasi_teks(
            aset.get("nomenklatur")
        )

        if nomenklatur:
            peta_nomenklatur.setdefault(
                nomenklatur, []
            ).append(aset)

    for laporan in daftar_laporan:
        nomenklatur = normalisasi_teks(
            laporan.get("nomenklatur")
        )

        kandidat = peta_nomenklatur.get(
            nomenklatur, []
        )

        aset_terpilih = (
            kandidat[0] if len(kandidat) == 1 else None
        )

        metode = "nomenklatur" if aset_terpilih else None
        jarak_terdekat = None

        # Jika nomenklatur tidak cocok atau ambigu,
        # gunakan pencocokan berdasarkan koordinat.
        if aset_terpilih is None:
            lon, lat, status_koordinat_laporan = normalisasi_koordinat(
                laporan.get("lon"),
                laporan.get("lat")
            )

            if lon is not None and lat is not None:
                titik_laporan = Point(lon, lat)

                titik_laporan_utm = transform(
                    transformer_wgs84_to_utm.transform,
                    titik_laporan
                )

                for aset in daftar_aset:
                    aset_lon, aset_lat, _ = normalisasi_koordinat(
                        aset.get("x"),
                        aset.get("y")
                    )

                    if aset_lon is None or aset_lat is None:
                        continue

                    titik_aset = transform(
                        transformer_wgs84_to_utm.transform,
                        Point(aset_lon, aset_lat)
                    )

                    jarak = titik_laporan_utm.distance(
                        titik_aset
                    )

                    if (
                        jarak <= jarak_maksimal
                        and (
                            jarak_terdekat is None
                            or jarak < jarak_terdekat
                        )
                    ):
                        jarak_terdekat = jarak
                        aset_terpilih = aset
                        metode = "koordinat"

        hasil.append({
            **laporan,
            "kode_aset": (
                aset_terpilih.get("kode_aset")
                if aset_terpilih else None
            ),
            "metode_pencocokan": metode,
            "status_koordinat_laporan": (
                status_koordinat_laporan
                if aset_terpilih is None or metode == "koordinat"
                else None
            ),
            "jarak_pencocokan_meter": (
                round(jarak_terdekat, 2)
                if jarak_terdekat is not None
                else None
            )
        })

    return hasil

# PENGUJIAN NORMALISASI KOORDINAT

if __name__ == "__main__":


    contoh_koordinat = [
        ("WGS84", 110.38581, -7.640567),
        ("Tertukar", -7.640567, 110.38581),
        ("UTM", 433395.84, 9160024.52),
        ("UTM tertukar", 9160024.52, 433395.84),
        ("Koordinat nol", 0, 0),
        ("Koordinat kosong", None, None),
    ]

    for nama, x, y in contoh_koordinat:
        lon, lat, status = normalisasi_koordinat(x, y)

        print(f"\nPengujian: {nama}")
        print(f"Input     : X={x}, Y={y}")
        print(f"Longitude : {lon}")
        print(f"Latitude  : {lat}")
        print(f"Status   : {status}")

    print("\n=== UJI GEOMETRI SALURAN ===")

    with open("data/saluran.geojson", "r", encoding="utf-8") as file:
        geojson_saluran = json.load(file)

    for feature in geojson_saluran["features"][:3]:
        geom, status = normalisasi_geometri(feature["geometry"])

        print(
            feature["properties"].get("id_ruas"),
            "|",
            geom.geom_type if geom else None,
            "|",
            status
        )

    print("\n=== UJI GEOMETRI PETAK ===")

    with open("data/petak_tersier.geojson", "r", encoding="utf-8") as file:
        geojson_petak = json.load(file)

    for feature in geojson_petak["features"][:3]:
        geom, status = normalisasi_geometri(feature["geometry"])

        print(
            feature["properties"].get("kode_petak"),
            "|",
            geom.geom_type if geom else None,
            "|",
            status
        )
    
    # PENGUJIAN VALIDITAS SELURUH GEOMETRI

    print("\n=== VALIDASI SELURUH GEOMETRI ===")

    statistik = {
        "valid": 0,
        "diperbaiki": 0,
        "geometri_tidak_valid": 0,
        "geometri_kosong": 0
    }

    # Periksa seluruh saluran
    for feature in geojson_saluran["features"]:
        geom, status_normalisasi = normalisasi_geometri(
            feature["geometry"]
        )

        geom, status_validasi = perbaiki_geometri(geom)

        statistik[status_validasi] += 1

    # Periksa seluruh petak
    for feature in geojson_petak["features"]:
        geom, status_normalisasi = normalisasi_geometri(
            feature["geometry"]
        )

        geom, status_validasi = perbaiki_geometri(geom)

        statistik[status_validasi] += 1

    print("Total geometri:", sum(statistik.values()))

    for status, jumlah in statistik.items():
        print(f"{status}: {jumlah}")
    

        # PENGUJIAN PANJANG SALURAN

    print("\n=== PERHITUNGAN PANJANG SALURAN ===")

    daftar_panjang = []
    total_panjang = 0

    for feature in geojson_saluran["features"]:
        properties = feature.get("properties", {})

        geom, status = normalisasi_geometri(
            feature["geometry"]
        )

        geom, status_validasi = perbaiki_geometri(geom)

        if geom is None:
            continue

        panjang = hitung_panjang_saluran(geom)

        daftar_panjang.append({
            "id_ruas": properties.get("id_ruas"),
            "nama_saluran": properties.get("nama_saluran"),
            "panjang_meter": panjang
        })

        total_panjang += panjang

    # Tampilkan 5 contoh ruas
    for ruas in daftar_panjang[:5]:
        print(
            ruas["id_ruas"],
            "|",
            ruas["nama_saluran"],
            "|",
            round(ruas["panjang_meter"], 2),
            "meter"
        )

    print("Jumlah ruas berhasil dihitung:", len(daftar_panjang))
    print("Total panjang jaringan:", round(total_panjang, 2), "meter")
    print("Total panjang jaringan:", round(total_panjang / 1000, 3), "km")

    #   # PENGUJIAN LUAS PETAK TERSIER

    # print("\n=== PERHITUNGAN LUAS PETAK ===")

    # petak_unik, duplikat_petak = deduplikasi_petak(geojson_petak["features"])
    # print("Total petak sebelum deduplikasi:", len(geojson_petak["features"]))
    # print("Total petak setelah deduplikasi:", len(petak_unik))
    # print("Kode petak duplikat:", duplikat_petak)
    
    # daftar_luas = []
    # total_luas = 0
    # jumlah_anomali = 0

    # for feature in petak_unik:
    #     properties = feature.get("properties", {})

    #     geom, status = normalisasi_geometri(
    #         feature["geometry"]
    #     )

    #     geom, status_validasi = perbaiki_geometri(geom)

    #     if geom is None:
    #         print(
    #             "GEOMETRI GAGAL",
    #             feature.get('properties', {}).get('kode_petak'),
    #         )
    #         continue

    #     luas_ha = hitung_luas_petak(geom)

    #     luas_baku = properties.get(
    #         "luas_baku",
    #         properties.get("luas_bak")
    #     )

    #     luas_baku = normalisasi_angka(luas_baku)

    #     # Deteksi kemungkinan satuan luas baku m²
    #     if luas_baku is not None and luas_baku > 1000:
    #         luas_baku = luas_baku / 10000

    #     selisih_persen = None

    #     if luas_baku is not None and luas_baku > 0:
    #         selisih_persen = abs(
    #             (luas_ha - luas_baku) / luas_baku
    #         ) * 100

    #     anomali = (
    #         selisih_persen is not None
    #         and selisih_persen > 20
    #     )

    #     if anomali:
    #         jumlah_anomali += 1

    #     daftar_luas.append({
    #         "kode_petak": properties.get("kode_petak"),
    #         "luas_geometri_ha": luas_ha,
    #         "luas_baku_ha": luas_baku,
    #         "selisih_persen": selisih_persen,
    #         "anomali": anomali
    #     })

    #     total_luas += luas_ha

    # # Tampilkan 5 contoh petak
    # for petak in daftar_luas[:5]:
    #     print(
    #         petak["kode_petak"],
    #         "| Geometri:",
    #         round(petak["luas_geometri_ha"], 2), "ha",
    #         "| Luas baku:",
    #         round(petak["luas_baku_ha"], 2)
    #         if petak["luas_baku_ha"] is not None else None,
    #         "ha",
    #         "| Selisih:",
    #         round(petak["selisih_persen"], 2)
    #         if petak["selisih_persen"] is not None else None,
    #         "%",
    #         "| Anomali:",
    #         petak["anomali"]
    #     )

    # print("Jumlah petak berhasil dihitung:", len(daftar_luas))
    # print("Total luas geometris:", round(total_luas, 2), "ha")
    # print("Petak dengan selisih >20%:", jumlah_anomali)

    # print("\n=== DETAIL PETAK ANOMALI ===")

    # for petak in daftar_luas:
    #     if petak["anomali"]:
    #         print(
    #             petak["kode_petak"],
    #             "| Geometri:",
    #             round(petak["luas_geometri_ha"], 2), "ha",
    #             "| Luas baku:",
    #             round(petak["luas_baku_ha"], 2), "ha",
    #             "| Selisih:",
    #             round(petak["selisih_persen"], 2), "%"
    #         )

    # PENGUJIAN FUNGSI PROSES PETAK

    print("\n=== UJI FUNGSI PROSES PETAK ===")

    hasil_petak = proses_petak_tersier(
        geojson_petak["features"]
    )

    print("Total awal:", hasil_petak["total_awal"])
    print("Total unik:", hasil_petak["total_unik"])
    print("Duplikat:", hasil_petak["duplikat"])
    print("Berhasil dihitung:", hasil_petak["jumlah_berhasil"])
    print("Geometri gagal:", hasil_petak["geometri_gagal"])
    print("Total luas:", hasil_petak["total_luas_ha"], "ha")
    print("Jumlah anomali:", hasil_petak["jumlah_anomali"])

    print("\n=== DETAIL ANOMALI LUAS PETAK ===")

    for petak in hasil_petak["data"]:
        if petak["anomali"]:
            print(
                f'{petak["kode_petak"]} | '
                f'Geometri: {petak["luas_geometri_ha"]} ha | '
                f'Luas baku: {petak["luas_baku_ha"]} ha | '
                f'Selisih: {petak["selisih_persen"]}%'
            )
    
    print("\n=== UJI PENGELOMPOKAN SALURAN ===")

    data_saluran = bersihkan_saluran(
        "data/saluran.geojson"
    )
    print("Contoh data saluran:", data_saluran[0])

    kelompok = kelompokkan_saluran(data_saluran)

    for nama, ruas in kelompok.items():
        print(f"{nama} | Jumlah ruas: {len(ruas)}")

    print("Total kelompok:", len(kelompok))
    print("Total ruas:", sum(len(ruas) for ruas in kelompok.values()))

    print("\n=== UJI PENGGABUNGAN GEOMETRI SALURAN ===")

    hasil_gabungan = gabungkan_geometri_saluran(data_saluran)

    total_ruas = 0

    for nama, data in hasil_gabungan.items():
        panjang = hitung_panjang_saluran(data["geometry"])
        total_ruas += data["jumlah_ruas"]

        print(
            f"{nama} | "
            f"Ruas: {data['jumlah_ruas']} | "
            f"Panjang: {round(panjang, 2)} meter"
        )

    print("Total kelompok:", len(hasil_gabungan))
    print("Total ruas tergabung:", total_ruas)


    print("\n=== UJI KONEKSI ANTAR-RUAS ===")

    ruas_unik, duplikat = deduplikasi_saluran(data_saluran)
    ruas_valid = []

    for saluran in ruas_unik:
        geom, status = normalisasi_geometri(
            saluran.get("geometry")
        )

        geom, status_validasi = perbaiki_geometri(geom)

        if geom is not None and geom.geom_type == "LineString":
            ruas_valid.append({
                "id_ruas": saluran["id_ruas"],
                "nama_saluran": saluran["nama_saluran"],
                "geometry": geom
            })

    total_koneksi = 0

    for i in range(len(ruas_valid)):
        for j in range(i + 1, len(ruas_valid)):
            if ruas_valid[i]["id_ruas"] == ruas_valid[j]["id_ruas"]:
                continue
            koneksi = deteksi_koneksi_ruas(
                ruas_valid[i]["geometry"],
                ruas_valid[j]["geometry"]
            )

            if koneksi:
                for detail in koneksi:
                    total_koneksi += 1

                    print(
                        f"{ruas_valid[i]['id_ruas']} <-> "
                        f"{ruas_valid[j]['id_ruas']} | "
                        f"Ujung: {detail['ujung_a']} <-> {detail['ujung_b']} | "
                        f"Jarak: {detail['jarak_meter']} meter"
                    )

    print("Total ruas diperiksa:", len(ruas_valid))
    print("Total koneksi titik ujung:", total_koneksi)

    print("\n=== UJI DUPLIKAT GEOMETRI SALURAN ===")

    duplikat_saluran = deteksi_duplikat_geometri_saluran(
        data_saluran
    )

    if duplikat_saluran:
        for item in duplikat_saluran:
            print(
                f"{item['id_ruas_a']} <-> {item['id_ruas_b']} | "
                f"{item['nama_a']} | {item['nama_b']}"
            )
    else:
        print("Tidak ditemukan geometri saluran duplikat.")

    print("Total duplikat geometri:", len(duplikat_saluran))
    

    print("\n=== UJI DEDUPLIKASI SALURAN ===")

    ruas_unik, duplikat = deduplikasi_saluran(data_saluran)

    print("Total ruas awal:", len(data_saluran))
    print("Total ruas unik:", len(ruas_unik))
    print("Total duplikat:", len(duplikat))

    for item in duplikat:
        print(
            f"{item['id_ruas']} | "
            f"Duplikat dari: {item['duplikat_dari']} | "
            f"Alasan: {item['alasan']}"
        )
    

    print("\n=== UJI GRAPH JARINGAN SALURAN ===")

    ruas_unik, duplikat = deduplikasi_saluran(data_saluran)

    graph = bangun_graph_saluran(ruas_unik)

    print("Total node:", graph.number_of_nodes())
    print("Total edge:", graph.number_of_edges())
    print("Jumlah komponen jaringan:", nx.number_connected_components(graph))

    print("\nDaftar hubungan antar-ruas:")

    for ruas_a, ruas_b, data in graph.edges(data=True):
        print(
            f"{ruas_a} <-> {ruas_b} | "
            f"Koneksi: {data['jumlah_koneksi']} | "
            f"Jarak minimum: {data['jarak_minimum']} meter"
        )

    