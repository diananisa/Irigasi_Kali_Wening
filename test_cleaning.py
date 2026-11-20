import os
import re
from datetime import date, datetime

import pytest

from cleaning import (
    bersihkan_aset,
    bersihkan_laporan,
    bersihkan_petak,
    bersihkan_saluran,
    normalisasi_angka,
    normalisasi_jenis,
    normalisasi_kondisi,
    normalisasi_nomenklatur,
    normalisasi_status,
    normalisasi_tanggal,
    normalisasi_teks,
    normalisasi_tingkat,
)

DATA_DIR = os.environ.get('DATA_DIR', 'data')


# ---------- fungsi tunggal (contoh nyata dari data tugas)

@pytest.mark.parametrize('mentah, hasil', [
    ('B.KW.1', 'B.KW.1'),
    ('BKW 1', 'B.KW.1'),
    ('bkw1', 'B.KW.1'),
    (' B-KW-2', 'B.KW.2'),
    ('b_wg_4 ', 'B.WG.4'),
    ('B.KW.6a', 'B.KW.6A'),
    ('b ka 3b', 'B.KA.3B'),
    ('B TS 2a', 'B.TS.2A'),
    ('BTS 1', 'B.TS.1'),
    ('', None),
    (None, None),
])
def test_nomenklatur(mentah, hasil):
    assert normalisasi_nomenklatur(mentah) == hasil


def test_nomenklatur_tidak_berpola_tidak_hilang():
    assert normalisasi_nomenklatur('xyz 9') == 'XYZ 9'


def test_kunci_pencocokan_sama_untuk_semua_penulisan():
    assert normalisasi_teks('B.KW.1') == normalisasi_teks('bkw 1') == 'BKW1'


@pytest.mark.parametrize('mentah, hasil', [
    ('RR', 'rusak_ringan'),
    ('Rusak Ringan', 'rusak_ringan'),
    ('rusak ringan ', 'rusak_ringan'),
    ('Rusak_Ringan', 'rusak_ringan'),
    ('rusak  sedang', 'rusak_sedang'),
    ('RS', 'rusak_sedang'),
    ('Rusak-Berat', 'rusak_berat'),
    ('rb', 'rusak_berat'),
    ('BAIK ', 'baik'),
    ('b', 'baik'),
    ('entah', None),
    ('', None),
])
def test_kondisi(mentah, hasil):
    assert normalisasi_kondisi(mentah) == hasil


@pytest.mark.parametrize('mentah, hasil', [
    ('Bangunan Sadap', 'bangunan_sadap'),
    ('BANGUNAN SADAP', 'bangunan_sadap'),
    ('Bangunan Bagi-Sadap', 'bangunan_bagi_sadap'),
    ('bangunan_bagi_sadap', 'bangunan_bagi_sadap'),
    ('Bangunan Bagi', 'bangunan_bagi'),
    ('Bendung', 'bendung'),
    ('Gorong-gorong', 'bangunan_pelengkap'),
    ('talang', 'bangunan_pelengkap'),
    ('siphon', 'bangunan_pelengkap'),
    ('Terjunan', 'bangunan_pelengkap'),
    ('lainnya', None),
])
def test_jenis(mentah, hasil):
    assert normalisasi_jenis(mentah) == hasil


def test_tingkat_dan_status():
    assert normalisasi_tingkat(' Sekunder') == 'sekunder'
    assert normalisasi_tingkat('PRIMER') == 'primer'
    assert normalisasi_status('AKTIF') == 'aktif'
    assert normalisasi_status('Batal') == 'batal'
    assert normalisasi_status('') is None


@pytest.mark.parametrize('mentah, hasil', [
    ('31-12-2025', date(2025, 12, 31)),
    ('14/06/2025', date(2025, 6, 14)),
    ('2025/03/12', date(2025, 3, 12)),
    ('2026-06-28 00:00:00', date(2026, 6, 28)),
    ('22 Agustus 2026', date(2026, 8, 22)),
    ('24 agustus 2026', date(2026, 8, 24)),
    ('08-03-2026', date(2026, 3, 8)),     # ambigu: hari dulu
    ('6/1/2026', date(2026, 1, 6)),       # ambigu: hari dulu
    ('2/6/2026', date(2026, 6, 2)),
    ('3/25/2026', date(2026, 3, 25)),     # jelas bulan-dulu
    (datetime(2026, 4, 24, 0, 0), date(2026, 4, 24)),
    ('31/02/2026', None),
    ('bukan tanggal', None),
    ('', None),
])
def test_tanggal(mentah, hasil):
    assert normalisasi_tanggal(mentah) == hasil


@pytest.mark.parametrize('mentah, hasil', [
    ('110,402958', 110.402958),
    ('-7,687024', -7.687024),
    ('38,6', 38.6),
    ('1.234,5', 1234.5),
    ('1,234.5', 1234.5),
    ('437888.80', 437888.8),
    (412000, 412000.0),
    ('', None),
    (None, None),
    ('abc', None),
])
def test_angka(mentah, hasil):
    assert normalisasi_angka(mentah) == hasil


# ---------- integrasi: keluaran harus sesuai kontrak API

pytestmark_data = pytest.mark.skipif(
    not os.path.exists(os.path.join(DATA_DIR, 'aset_bangunan.csv')),
    reason='folder data tidak ditemukan (atur DATA_DIR)',
)

POLA_NOMEN = re.compile(r'B\.[A-Z]{2,3}\.\d+[A-Z]*')
KONDISI = {'baik', 'rusak_ringan', 'rusak_sedang', 'rusak_berat'}
JENIS = {'bendung', 'bangunan_bagi', 'bangunan_sadap', 'bangunan_bagi_sadap', 'bangunan_pelengkap'}


@pytestmark_data
def test_aset_sesuai_kontrak():
    aset = bersihkan_aset(os.path.join(DATA_DIR, 'aset_bangunan.csv'))
    assert aset
    for a in aset:
        assert a['nomenklatur'] is None or POLA_NOMEN.fullmatch(a['nomenklatur']), a
        assert a['kondisi'] in KONDISI, a
        assert a['jenis'] in JENIS, a
        assert isinstance(a['tgl_update'], date), a


@pytestmark_data
@pytest.mark.parametrize('nama', ['laporan_penelusuran.xlsx', 'laporan_susulan.xlsx'])
def test_laporan_sesuai_kontrak(nama):
    laporan = bersihkan_laporan(os.path.join(DATA_DIR, nama))
    assert laporan
    for x in laporan:
        assert x['nomenklatur'] is None or POLA_NOMEN.fullmatch(x['nomenklatur']), x
        assert x['kondisi'] in KONDISI, x
        assert x['status'] in {'aktif', 'batal'}, x
        assert isinstance(x['tanggal'], date), x


@pytestmark_data
def test_saluran_dan_petak_sesuai_kontrak():
    saluran = bersihkan_saluran(os.path.join(DATA_DIR, 'saluran.geojson'))
    for s in saluran:
        assert s['tingkat'] in {'primer', 'sekunder'}, s
        assert s['kondisi'] in KONDISI, s
    petak = bersihkan_petak(os.path.join(DATA_DIR, 'petak_tersier.geojson'))
    for p in petak:
        assert re.fullmatch(r'[A-Z]{2,3}\.\d+\.(Ki|Ka)', p['kode_petak']), p
        assert p['luas_baku'] is not None, p
        assert p['nomenklatur_sadap'] is None or POLA_NOMEN.fullmatch(p['nomenklatur_sadap']), p