import { useEffect, useState } from "react";
import {
  Building2,
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  Waves,
  ClipboardList,
  Ruler,
  TrendingUp,
} from "lucide-react";

import {
  getAset,
  getRekapSaluran,
  getPrioritas,
  getKualitasData,
} from "../services/api";

import MapIrigasi from "../components/MapIrigasi";

const labelKondisi = {
  baik: "Baik",
  rusak_ringan: "Rusak Ringan",
  rusak_sedang: "Rusak Sedang",
  rusak_berat: "Rusak Berat",
};

export default function Dashboard() {
  const [aset, setAset] = useState([]);
  const [rekapSaluran, setRekapSaluran] = useState(null);
  const [prioritas, setPrioritas] = useState([]);
  const [totalTemuan, setTotalTemuan] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      getAset(),
      getRekapSaluran(),
      getPrioritas(),
      getKualitasData(),
    ])
      .then(([resAset, resSaluran, resPrioritas, resKualitas]) => {
        setAset(resAset.data.data || []);
        setRekapSaluran(resSaluran.data);
        setPrioritas(resPrioritas.data.data || []);
        setTotalTemuan(resKualitas.data.total_temuan || 0);
      })
      .catch((err) => {
        console.error("Gagal mengambil ringkasan dashboard:", err);
        setError("Sebagian data dashboard gagal dimuat.");
      })
      .finally(() => setLoading(false));
  }, []);

  const jumlahKondisi = (kondisi) =>
    aset.filter((item) => item.kondisi === kondisi).length;

  const summary = [
    {
      title: "Total Aset",
      value: aset.length,
      description: "Aset bangunan terdaftar",
      icon: Building2,
    },
    {
      title: "Rusak Berat",
      value: jumlahKondisi("rusak_berat"),
      description: "Memerlukan penanganan",
      icon: AlertTriangle,
    },
    {
      title: "Panjang Saluran",
      value: rekapSaluran
        ? `${Number(rekapSaluran.total_panjang_km).toLocaleString("id-ID", {
            maximumFractionDigits: 2,
          })} km`
        : "-",
      description: "Total jaringan saluran",
      icon: Ruler,
    },
    {
      title: "Temuan Kualitas Data",
      value: totalTemuan,
      description: "Data yang perlu ditinjau",
      icon: ClipboardList,
    },
  ];

  const daftarKondisi = [
    { label: "Baik", key: "baik", color: "#16a34a" },
    { label: "Rusak Ringan", key: "rusak_ringan", color: "#eab308" },
    { label: "Rusak Sedang", key: "rusak_sedang", color: "#f97316" },
    { label: "Rusak Berat", key: "rusak_berat", color: "#dc2626" },
  ];

  const asetRusakBerat = aset.filter(
    (item) => item.kondisi === "rusak_berat"
  );

  const daftarPrioritas = prioritas.slice(0, 5);

  const formatAngka = (nilai) =>
    Number(nilai || 0).toLocaleString("id-ID", {
      maximumFractionDigits: 2,
    });

  return (
    <div className="dashboard">
      <div className="page-heading">
        <div>
          <h1>Ringkasan Kondisi Irigasi</h1>
          <p>Pantau kondisi aset dan jaringan irigasi DI Kali Wening.</p>
        </div>
      </div>

      {error && <p className="empty-state">{error}</p>}

      <div className="summary-grid">
        {summary.map((item) => {
          const Icon = item.icon;

          return (
            <div className="summary-card" key={item.title}>
              <div className="summary-card-top">
                <span>{item.title}</span>
                <div className="summary-icon">
                  <Icon size={21} />
                </div>
              </div>

              <h2>{loading ? "..." : item.value}</h2>
              <p>{item.description}</p>
            </div>
          );
        })}
      </div>

      <div className="dashboard-content">
        <section className="content-card">
          <div className="card-heading">
            <div>
              <h3>Peta Jaringan Irigasi</h3>
              <p>Visualisasi saluran dan bangunan irigasi</p>
            </div>
          </div>

          <MapIrigasi />
        </section>

        <section className="content-card">
          <div className="card-heading">
            <div>
              <h3>Kondisi Bangunan</h3>
              <p>Distribusi kondisi aset irigasi</p>
            </div>
          </div>

          {loading ? (
            <div className="empty-state">Memuat data aset...</div>
          ) : (
            <>
              <div className="condition-total">
                <div>
                  <span>Total Bangunan</span>
                  <h2>{aset.length}</h2>
                </div>
                <Building2 size={28} />
              </div>

              <div className="condition-list">
                {daftarKondisi.map((item) => {
                  const jumlah = jumlahKondisi(item.key);
                  const persen =
                    aset.length > 0 ? (jumlah / aset.length) * 100 : 0;

                  return (
                    <div className="condition-item" key={item.key}>
                      <div className="condition-label">
                        <span>
                          <i
                            className="condition-dot"
                            style={{ backgroundColor: item.color }}
                          />
                          {item.label}
                        </span>

                        <strong>
                          {jumlah} ({persen.toFixed(1)}%)
                        </strong>
                      </div>

                      <div className="condition-track">
                        <div
                          className="condition-fill"
                          style={{
                            width: `${persen}%`,
                            backgroundColor: item.color,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="damaged-assets">
                <h4>
                  <AlertTriangle size={16} />
                  Bangunan Rusak Berat
                </h4>

                {asetRusakBerat.length === 0 ? (
                  <p className="no-damaged">
                    Tidak ada bangunan rusak berat.
                  </p>
                ) : (
                  <div className="damaged-list">
                    {asetRusakBerat.map((item) => (
                      <div className="damaged-item" key={item.kode_aset}>
                        <div>
                          <strong>{item.kode_aset}</strong>
                          <span>
                            {item.nomenklatur || item.jenis || "Bangunan irigasi"}
                          </span>
                        </div>

                        <span className="damaged-badge">Rusak Berat</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </div>

      <div className="dashboard-extra-grid">
        <section className="content-card">
          <div className="card-heading">
            <div>
              <h3>Rekap Kondisi Saluran</h3>
              <p>Ringkasan kondisi jaringan irigasi</p>
            </div>
            <Waves size={21} />
          </div>

          {loading || !rekapSaluran ? (
            <div className="empty-state">Memuat rekap saluran...</div>
          ) : (
            <>
              <div className="canal-summary">
                <div>
                  <span>Total Saluran</span>
                  <strong>{rekapSaluran.total_saluran}</strong>
                </div>
                <div>
                  <span>Geometri Valid</span>
                  <strong>{rekapSaluran.jumlah_geometri_valid}</strong>
                </div>
              </div>

              {["primer", "sekunder"].map((tingkat) => {
                const data = rekapSaluran.ringkasan?.[tingkat];

                return (
                  <div className="canal-condition" key={tingkat}>
                    <h4>Saluran {tingkat === "primer" ? "Primer" : "Sekunder"}</h4>

                    <div className="canal-condition-list">
                      {daftarKondisi.map((item) => (
                        <div key={item.key}>
                          <span>
                            <i
                              className="condition-dot"
                              style={{ backgroundColor: item.color }}
                            />
                            {item.label}
                          </span>
                          <strong>{data?.kondisi?.[item.key] || 0}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </section>

        <section className="content-card">
          <div className="card-heading">
            <div>
              <h3>Prioritas Rehabilitasi</h3>
              <p>Lima aset dengan skor prioritas tertinggi</p>
            </div>
            <TrendingUp size={21} />
          </div>

          {loading ? (
            <div className="empty-state">Memuat data prioritas...</div>
          ) : daftarPrioritas.length === 0 ? (
            <div className="empty-state">Belum ada data prioritas.</div>
          ) : (
            <div className="dashboard-priority-list">
              {daftarPrioritas.map((item, index) => (
                <div className="dashboard-priority-item" key={item.kode_aset}>
                  <div className="priority-rank">{index + 1}</div>

                  <div className="priority-info">
                    <strong>{item.kode_aset}</strong>
                    <span>
                      {item.id_ruas || "-"} ·{" "}
                      {labelKondisi[item.kondisi] || item.kondisi}
                    </span>
                  </div>

                  <div className="priority-score">
                    <strong>{formatAngka(item.skor_prioritas)}</strong>
                    <span>Skor</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="dashboard-priority-footer">
            <span>Total aset dalam prioritas</span>
            <strong>{loading ? "..." : prioritas.length}</strong>
          </div>
        </section>
      </div>
    </div>
  );
}