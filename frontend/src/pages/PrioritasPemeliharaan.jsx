import { useEffect, useState } from "react";
import {
  ClipboardList,
  AlertTriangle,
  TrendingUp,
  RefreshCw,
} from "lucide-react";

import { getPrioritas } from "../services/api";

const formatAngka = (nilai) =>
  Number(nilai || 0).toLocaleString("id-ID", {
    maximumFractionDigits: 2,
  });

const formatKondisi = (kondisi) => {
  const label = {
    baik: "Baik",
    rusak_ringan: "Rusak Ringan",
    rusak_sedang: "Rusak Sedang",
    rusak_berat: "Rusak Berat",
  };

  return label[kondisi] || kondisi || "-";
};

export default function PrioritasPemeliharaan() {
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const muatPrioritas = () => {
    setLoading(true);
    setError("");

    getPrioritas()
      .then((response) => {
        setData(response.data.data || []);
        setTotal(response.data.total || 0);
      })
      .catch((err) => {
        console.error("Gagal mengambil prioritas:", err);
        setError("Gagal mengambil data prioritas dari server.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    muatPrioritas();
  }, []);

  const totalLuas = data.reduce(
    (jumlah, item) => jumlah + Number(item.luas_terdampak_ha || 0),
    0
  );

  const totalSkor = data.reduce(
    (jumlah, item) => jumlah + Number(item.skor_prioritas || 0),
    0
  );

  return (
    <div className="dashboard">
      <div className="page-heading">
        <div>
          <h1>Prioritas Pemeliharaan</h1>
          <p>
            Peringkat bangunan berdasarkan kondisi kerusakan dan luas
            petak yang terdampak.
          </p>
        </div>

        <button
          type="button"
          className="refresh-button"
          onClick={muatPrioritas}
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
            <span>Total Prioritas</span>
            <div className="summary-icon">
              <ClipboardList size={21} />
            </div>
          </div>
          <h2>{loading ? "..." : total}</h2>
          <p>Bangunan memerlukan penanganan</p>
        </div>

        <div className="summary-card">
          <div className="summary-card-top">
            <span>Total Luas Terdampak</span>
            <div className="summary-icon">
              <AlertTriangle size={21} />
            </div>
          </div>
          <h2>{loading ? "..." : formatAngka(totalLuas)}</h2>
          <p>Akumulasi luas terdampak (ha)</p>
        </div>

        <div className="summary-card">
          <div className="summary-card-top">
            <span>Total Skor</span>
            <div className="summary-icon">
              <TrendingUp size={21} />
            </div>
          </div>
          <h2>{loading ? "..." : formatAngka(totalSkor)}</h2>
          <p>Akumulasi skor seluruh prioritas</p>
        </div>
      </div>

      <section className="content-card">
        <div className="card-heading">
          <div>
            <h3>Peringkat Prioritas Rehabilitasi</h3>
            <p>Diurutkan dari skor prioritas tertinggi.</p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">Memuat data prioritas...</div>
        ) : data.length === 0 ? (
          <div className="empty-state">
            Tidak ada bangunan dalam daftar prioritas.
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Peringkat</th>
                  <th>Kode Aset</th>
                  <th>Ruas Saluran</th>
                  <th>Kondisi</th>
                  <th>Bobot</th>
                  <th>Luas Terdampak (ha)</th>
                  <th>Skor Prioritas</th>
                </tr>
              </thead>

              <tbody>
                {data.map((item, index) => (
                  <tr key={item.kode_aset}>
                    <td>
                      <strong>#{index + 1}</strong>
                    </td>
                    <td>
                      <strong>{item.kode_aset}</strong>
                    </td>
                    <td>{item.id_ruas || "-"}</td>
                    <td>
                      <span
                        className={`condition-badge ${item.kondisi || ""}`}
                      >
                        {formatKondisi(item.kondisi)}
                      </span>
                    </td>
                    <td>{item.bobot_kondisi}</td>
                    <td>{formatAngka(item.luas_terdampak_ha)}</td>
                    <td>
                      <strong>{formatAngka(item.skor_prioritas)}</strong>
                    </td>
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