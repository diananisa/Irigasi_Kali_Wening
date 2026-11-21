import { useEffect, useState } from "react";
import {
  Database,
  AlertTriangle,
  FileSearch,
  RefreshCw,
} from "lucide-react";

import { getKualitasData } from "../services/api";

const labelMasalah = {
  koordinat_tertukar: "Koordinat Tertukar",
  jauh_dari_saluran: "Jauh dari Saluran",
  koordinat_tidak_valid: "Koordinat Tidak Valid",
  duplikasi_aset: "Duplikasi Aset",
  duplikasi_saluran: "Duplikasi Saluran",
  laporan_tidak_terhubung: "Laporan Tidak Terhubung",
  duplikasi_petak: "Duplikasi Petak",
  anomali_luas_petak: "Anomali Luas Petak",
};

const formatAngka = (nilai) =>
  Number(nilai || 0).toLocaleString("id-ID", {
    maximumFractionDigits: 2,
  });

export default function KualitasData() {
  const [data, setData] = useState([]);
  const [ringkasan, setRingkasan] = useState({});
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const muatKualitasData = () => {
    setLoading(true);
    setError("");

    getKualitasData()
      .then((response) => {
        setData(response.data.data || []);
        setRingkasan(response.data.ringkasan || {});
        setTotal(response.data.total_temuan || 0);
      })
      .catch((err) => {
        console.error("Gagal mengambil kualitas data:", err);
        setError("Gagal mengambil data kualitas dari server.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    muatKualitasData();
  }, []);

  const totalSumber = new Set(
    data
      .map((item) => item.sumber)
      .filter((sumber) => sumber)
  ).size;

  return (
    <div className="dashboard">
      <div className="page-heading">
        <div>
          <h1>Kualitas Data</h1>
          <p>
            Pemeriksaan anomali, duplikasi, koordinat, dan keterhubungan
            data jaringan irigasi.
          </p>
        </div>

        <button
          type="button"
          className="refresh-button"
          onClick={muatKualitasData}
          disabled={loading}
        >
          <RefreshCw size={16} />
          Muat Ulang
        </button>
      </div>

      {error && <p className="empty-state">{error}</p>}

      <div className="summary-grid">
        <div className="summary-card">
          <div className="summary-card-top">
            <span>Total Temuan</span>
            <div className="summary-icon">
              <Database size={21} />
            </div>
          </div>
          <h2>{loading ? "..." : total}</h2>
          <p>Temuan validasi data</p>
        </div>

        <div className="summary-card">
          <div className="summary-card-top">
            <span>Jenis Masalah</span>
            <div className="summary-icon">
              <AlertTriangle size={21} />
            </div>
          </div>
          <h2>{loading ? "..." : Object.keys(ringkasan).length}</h2>
          <p>Kategori pemeriksaan</p>
        </div>

        <div className="summary-card">
          <div className="summary-card-top">
            <span>Sumber Data</span>
            <div className="summary-icon">
              <FileSearch size={21} />
            </div>
          </div>
          <h2>{loading ? "..." : totalSumber}</h2>
          <p>File sumber dengan temuan</p>
        </div>
      </div>

      <section className="content-card">
        <div className="card-heading">
          <div>
            <h3>Ringkasan Temuan</h3>
            <p>Jumlah masalah berdasarkan kategori.</p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">Memuat ringkasan...</div>
        ) : (
          <div className="quality-summary-grid">
            {Object.entries(ringkasan).map(([jenis, jumlah]) => (
              <div className="quality-summary-item" key={jenis}>
                <span>{labelMasalah[jenis] || jenis}</span>
                <strong>{jumlah}</strong>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="content-card">
        <div className="card-heading">
          <div>
            <h3>Detail Temuan Kualitas Data</h3>
            <p>
              Informasi sumber data, lokasi temuan, dan saran tindakan.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">Memuat detail temuan...</div>
        ) : data.length === 0 ? (
          <div className="empty-state">
            Tidak ditemukan masalah kualitas data.
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>No.</th>
                  <th>Jenis Masalah</th>
                  <th>Kategori</th>
                  <th>Kode</th>
                  <th>Sumber</th>
                  <th>Baris/Fitur</th>
                  <th>Detail</th>
                  <th>Saran Tindakan</th>
                </tr>
              </thead>

              <tbody>
                {data.map((item, index) => (
                  <tr
                    key={`${item.jenis_masalah}-${item.kode}-${index}`}
                  >
                    <td>{index + 1}</td>
                    <td>
                      <span className="quality-badge">
                        {labelMasalah[item.jenis_masalah] ||
                          item.jenis_masalah}
                      </span>
                    </td>
                    <td>{item.kategori}</td>
                    <td>
                      <strong>{item.kode || "-"}</strong>
                    </td>
                    <td>{item.sumber || "-"}</td>
                    <td>{item.baris_atau_fitur ?? "-"}</td>
                    <td>
                      <div className="quality-detail">
                        {item.detail}

                        {item.jarak_meter != null && (
                          <small>
                            Jarak: {formatAngka(item.jarak_meter)} meter
                          </small>
                        )}

                        {item.luas_geometri_ha != null && (
                          <small>
                            Luas geometri:{" "}
                            {formatAngka(item.luas_geometri_ha)} ha
                          </small>
                        )}

                        {item.luas_baku_ha != null && (
                          <small>
                            Luas baku: {formatAngka(item.luas_baku_ha)} ha
                          </small>
                        )}
                      </div>
                    </td>
                    <td>{item.saran_tindakan || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}