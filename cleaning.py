import csv
import json
import math
import re
from datetime import date, datetime, timedelta

import openpyxl


# ==========================================
# UTILITAS
# ==========================================

def _kosong(nilai):
    if nilai is None:
        return True
    if isinstance(nilai, float) and math.isnan(nilai):
        return True
    return isinstance(nilai, str) and nilai.strip() == ''


def _teks(nilai):
    """Teks tanpa spasi tepi dan spasi ganda; kosong -> ''."""
    if _kosong(nilai):
        return ''
    return ' '.join(str(nilai).split())


def _kata(nilai):
    """Huruf kecil; _ - dan spasi berulang menjadi satu spasi."""
    return re.sub(r'[\s_\-]+', ' ', _teks(nilai).lower()).strip()


# ==========================================
# NORMALISASI TEKS / NOMENKLATUR
# ==========================================

def normalisasi_teks(nilai):
    """Kunci pencocokan: 'B.KW.1', 'BKW 1', 'bkw1' -> 'BKW1'.

    Dipakai untuk membandingkan dua nomenklatur. Untuk TAMPILAN dan API
    pakai normalisasi_nomenklatur().
    """
    if _kosong(nilai):
        return None
    nilai = re.sub(r'[\s._-]+', '', str(nilai).strip().upper())
    return nilai if nilai else None


_POLA_NOMENKLATUR = re.compile(r'B[\s._\-]*([A-Z]{2,3})[\s._\-]*(\d+)[\s._\-]*([A-Z]*)')


def normalisasi_nomenklatur(nilai):
    """'bkw1' -> 'B.KW.1'; 'B KW 6a' -> 'B.KW.6A'; 'b_wg_4 ' -> 'B.WG.4'.

    Kosong -> None. Teks yang tidak berpola dikembalikan dalam huruf besar
    apa adanya, supaya pencocokan menilainya 'tidak dikenal'.
    """
    if _kosong(nilai):
        return None
    s = str(nilai).strip().upper()
    m = _POLA_NOMENKLATUR.fullmatch(s)
    if not m:
        return s
    return f'B.{m.group(1)}.{m.group(2)}{m.group(3)}'


# ==========================================
# NORMALISASI KATEGORI
# ==========================================

_KONDISI = {
    'baik': 'baik', 'b': 'baik',
    'rusak ringan': 'rusak_ringan', 'rr': 'rusak_ringan', 'ringan': 'rusak_ringan',
    'rusak sedang': 'rusak_sedang', 'rs': 'rusak_sedang', 'sedang': 'rusak_sedang',
    'rusak berat': 'rusak_berat', 'rb': 'rusak_berat', 'berat': 'rusak_berat',
}


def normalisasi_kondisi(nilai):
    """-> baik | rusak_ringan | rusak_sedang | rusak_berat | None."""
    return _KONDISI.get(_kata(nilai))


def normalisasi_status(nilai):
    """-> aktif | batal | None."""
    s = _kata(nilai)
    if 'batal' in s:
        return 'batal'
    if 'aktif' in s:
        return 'aktif'
    return None


def normalisasi_tingkat(nilai):
    """-> primer | sekunder | None."""
    s = _kata(nilai)
    if s.startswith('prim'):
        return 'primer'
    if s.startswith('sek'):
        return 'sekunder'
    return None


def normalisasi_jenis(nilai):
    """-> bendung | bangunan_bagi | bangunan_sadap | bangunan_bagi_sadap |
    bangunan_pelengkap | None."""
    s = _kata(nilai)
    if not s:
        return None
    if 'bendung' in s:
        return 'bendung'
    if 'bagi' in s and 'sadap' in s:
        return 'bangunan_bagi_sadap'
    if 'sadap' in s:
        return 'bangunan_sadap'
    if 'bagi' in s:
        return 'bangunan_bagi'
    if any(k in s for k in ('gorong', 'talang', 'siphon', 'sifon', 'terjun', 'pelengkap')):
        return 'bangunan_pelengkap'
    return None


# ==========================================
# NORMALISASI ANGKA
# ==========================================

def normalisasi_angka(nilai):
    """'110,402958' -> 110.402958 ; '1.234,5' -> 1234.5 ; kosong/rusak -> None."""
    if _kosong(nilai):
        return None
    if isinstance(nilai, bool):
        return None
    if isinstance(nilai, (int, float)):
        return float(nilai)

    s = re.sub(r'[\s ]', '', str(nilai))
    if ',' in s and '.' in s:
        # pemisah yang muncul paling akhir adalah desimal
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '') if s.count(',') > 1 else s.replace(',', '.')
    elif s.count('.') > 1:
        s = s.replace('.', '')

    try:
        return float(s)
    except ValueError:
        return None


# ==========================================
# NORMALISASI TANGGAL
# ==========================================

_BULAN = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mei': 5, 'may': 5, 'jun': 6,
    'jul': 7, 'agu': 8, 'agt': 8, 'aug': 8, 'sep': 9, 'okt': 10, 'oct': 10,
    'nov': 11, 'des': 12, 'dec': 12,
}


def _buat_tanggal(tahun, bulan, hari):
    try:
        return date(int(tahun), int(bulan), int(hari))
    except ValueError:
        return None


def normalisasi_tanggal(nilai):
    """Berbagai format -> datetime.date. Yang ambigu dibaca hari lebih dulu.

    Dikenali: objek date/datetime, nomor seri Excel, 2026-06-28 (boleh ada
    jam), 2026/6/28, 28-06-2026, 28/6/2026, '22 Agustus 2026'.
    Format bulan-dulu hanya dipakai bila jelas (mis. 3/25/2026).
    Gagal -> None.
    """
    if _kosong(nilai):
        return None
    if isinstance(nilai, datetime):
        return nilai.date()
    if isinstance(nilai, date):
        return nilai
    if isinstance(nilai, (int, float)) and not isinstance(nilai, bool):
        if 20000 < nilai < 80000:
            return date(1899, 12, 30) + timedelta(days=int(nilai))
        return None

    s = str(nilai).strip()

    m = re.match(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)', s)
    if m:
        return _buat_tanggal(m.group(1), m.group(2), m.group(3))

    m = re.fullmatch(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?:[ T].*)?', s)
    if m:
        hari, bulan, tahun = int(m.group(1)), int(m.group(2)), m.group(3)
        if bulan > 12 >= hari:
            hari, bulan = bulan, hari
        return _buat_tanggal(tahun, bulan, hari)

    m = re.fullmatch(r'(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})', s)
    if m and m.group(2)[:3].lower() in _BULAN:
        return _buat_tanggal(m.group(3), _BULAN[m.group(2)[:3].lower()], m.group(1))

    return None


# ==========================================
# CLEANING DATA ASET BANGUNAN
# ==========================================

def _kunci_kecil(baris):
    return {str(k).strip().lower(): v for k, v in baris.items() if k is not None}


def bersihkan_aset(path):
    hasil = []
    nama_sumber = str(path).replace("\\", "/").rsplit("/", 1)[-1]

    with open(path, mode='r', encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)

        for mentah in reader:
            baris = _kunci_kecil(mentah)

            aset = {
                'kode_aset': _teks(baris.get('kode_aset')),
                'nomenklatur': normalisasi_nomenklatur(baris.get('nomenklatur')),
                'jenis': normalisasi_jenis(baris.get('jenis')),
                'nama_saluran': _teks(baris.get('nama_saluran')),
                'x': normalisasi_angka(baris.get('x')),
                'y': normalisasi_angka(baris.get('y')),
                'kondisi': normalisasi_kondisi(baris.get('kondisi')),
                'tahun_bangun': normalisasi_angka(baris.get('tahun_bangun')),
                'tgl_update': normalisasi_tanggal(baris.get('tgl_update')),

                # Identitas sumber data
                'sumber': nama_sumber,
                'baris_sumber': reader.line_num,
                'x_sumber': baris.get('x'),
                'y_sumber': baris.get('y')
            }

            hasil.append(aset)

    return hasil

# ==========================================
# CLEANING DATA LAPORAN
# ==========================================

def bersihkan_laporan(path):
    hasil = []
    nama_sumber = str(path).replace("\\", "/").rsplit("/", 1)[-1]

    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook.active

    header = [str(cell.value).strip().lower() for cell in sheet[1]]

    for nomor_baris, row in enumerate(
        sheet.iter_rows(min_row=2, values_only=True),
        start=2
    ):
        baris = dict(zip(header, row))

        if all(_kosong(v) for v in row):
            continue

        laporan = {
            'id_laporan': _teks(baris.get('id_laporan')),
            'tanggal': normalisasi_tanggal(baris.get('tanggal')),
            'petugas': _teks(baris.get('petugas')),
            'nomenklatur': normalisasi_nomenklatur(baris.get('nomenklatur')),
            'jenis_kerusakan': _teks(baris.get('jenis_kerusakan')).lower(),
            'kondisi': normalisasi_kondisi(baris.get('kondisi')),
            'lat': normalisasi_angka(baris.get('lat')),
            'lon': normalisasi_angka(baris.get('lon')),
            'status': normalisasi_status(baris.get('status')),
            'keterangan': _teks(baris.get('keterangan')),

            # Identitas sumber data
            'sumber': nama_sumber,
            'baris_sumber': nomor_baris
        }

        hasil.append(laporan)

    workbook.close()
    return hasil

# ==========================================
# CLEANING DATA SALURAN
# ==========================================

def bersihkan_saluran(path):
    with open(path, 'r', encoding='utf-8') as file:
        geojson = json.load(file)
        nama_sumber = str(path).replace("\\", "/").rsplit("/", 1)[-1]

    hasil = []
    for nomor_fitur, feature in enumerate(
    geojson.get('features', []),
    start=1
    ):
        properties = feature.get('properties') or {}

        saluran = {
            'id_ruas': _teks(properties.get('id_ruas')),
            'nama_saluran': _teks(properties.get('nama_saluran')),
            'tingkat': normalisasi_tingkat(properties.get('tingkat')),
            'kondisi': normalisasi_kondisi(properties.get('kondisi')),
            'geometry': feature.get('geometry'),
            'sumber': nama_sumber,
            'fitur_sumber': nomor_fitur
        }

        hasil.append(saluran)

    return hasil


# ==========================================
# CLEANING DATA PETAK TERSIER
# ==========================================

def bersihkan_petak(path):
    with open(path, 'r', encoding='utf-8') as file:
        geojson = json.load(file)
        nama_sumber = str(path).replace("\\", "/").rsplit("/", 1)[-1]

    hasil = []

    for nomor_fitur, feature in enumerate(geojson.get('features', []), start=1):
        properties = feature.get('properties') or {}

        luas_baku = normalisasi_angka(
            properties.get('luas_baku', properties.get('luas_bak'))
        )

        petak = {
            # huruf kode petak dibiarkan (KW.3.Ki), hanya spasi tepi dibuang
            'kode_petak': _teks(properties.get('kode_petak')),
            'nama_petak': _teks(properties.get('nama_petak')),
            'luas_baku': luas_baku,
            'nomenklatur_sadap': normalisasi_nomenklatur(
                properties.get('nomenklatur_sadap')
            ),
            'geometry': feature.get('geometry'),
            'sumber': nama_sumber,
            'fitur_sumber': nomor_fitur,
        }

        hasil.append(petak)

    return hasil


if __name__ == '__main__':
    aset = bersihkan_aset('data/aset_bangunan.csv')
    laporan = bersihkan_laporan('data/laporan_penelusuran.xlsx')
    susulan = bersihkan_laporan('data/laporan_susulan.xlsx')
    saluran = bersihkan_saluran('data/saluran.geojson')
    petak = bersihkan_petak('data/petak_tersier.geojson')

    print('Total aset:', len(aset))
    print('Total laporan awal:', len(laporan))
    print('Total laporan susulan:', len(susulan))
    print('Total ruas saluran:', len(saluran))
    print('Total petak tersier:', len(petak))
    print('\nContoh aset:', aset[0])
    print('Contoh laporan:', laporan[0])
    print('Contoh saluran:', {k: v for k, v in saluran[0].items() if k != 'geometry'})
    print('Contoh petak:', {k: v for k, v in petak[0].items() if k != 'geometry'})