import { useEffect, useMemo, useState } from "react";
import { Search, Eye, X, Building2, MapPin, Info, Activity } from "lucide-react";
import { getAset, getDetailAset } from "../services/api";

const labelKondisi = {
  baik: "Baik",
  rusak_ringan: "Rusak Ringan",
  rusak_sedang: "Rusak Sedang",
  rusak_berat: "Rusak Berat",
};

const warnaKondisi = {
  baik: "#16a34a",
  rusak_ringan: "#ca8a04",
  rusak_sedang: "#ea580c",
  rusak_berat: "#dc2626",
};

export default function DataBangunan() {
  const [aset, setAset] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filterKondisi, setFilterKondisi] = useState("semua");
  const [filterJenis, setFilterJenis] = useState("semua");
  const [selected, setSelected] = useState(null);

  const [detailLoading, setDetailLoading] = useState(false);

  const handleDetail = async (kodeAset) => {
    try {
      setDetailLoading(true);
      setSelected(null);

      const response = await getDetailAset(kodeAset);

      setSelected(response.data);
    } catch (err) {
      console.error("Gagal mengambil detail aset:", err);
      alert("Gagal mengambil detail bangunan.");
    } finally {
      setDetailLoading(false);
    }
  };
  

  useEffect(() => {
    getAset()
      .then((response) => setAset(response.data.data || []))
      .catch((err) => {
        console.error(err);
        setError("Gagal mengambil data bangunan.");
      })
      .finally(() => setLoading(false));
  }, []);

  const daftarJenis = [
    ...new Set(aset.map((item) => item.jenis).filter(Boolean)),
  ].sort();

  const hasilFilter = useMemo(() => {
    return aset.filter((item) => {
      const kata = search.toLowerCase();

      const cocokSearch =
        String(item.kode_aset || "").toLowerCase().includes(kata) ||
        String(item.nomenklatur || "").toLowerCase().includes(kata) ||
        String(item.nama_saluran || "").toLowerCase().includes(kata);

      const cocokKondisi =
        filterKondisi === "semua" || item.kondisi === filterKondisi;

      const cocokJenis =
        filterJenis === "semua" || item.jenis === filterJenis;

      return cocokSearch && cocokKondisi && cocokJenis;
    });
  }, [aset, search, filterKondisi, filterJenis]);

  const formatKoordinat = (value) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(7) : value;
  };

  const detailFields = selected
  ? [
      ["Kode Aset", selected.data?.kode_aset],
      ["Nomenklatur", selected.data?.nomenklatur],
      ["Jenis Bangunan", selected.data?.jenis],
      ["Nama Saluran", selected.data?.nama_saluran],
      ["Tahun Dibangun", selected.data?.tahun_bangun],
      ["Tanggal Update", selected.data?.tgl_update],
      ["Kondisi", labelKondisi[selected.data?.kondisi] || selected.data?.kondisi],
      ["Longitude (X)", formatKoordinat(selected.data?.x)],
      ["Latitude (Y)", formatKoordinat(selected.data?.y)],
      ["Saluran Terdekat", selected.data?.saluran_terdekat],
      ["ID Ruas", selected.data?.id_ruas_terdekat],
      ["Jarak ke Saluran", selected.data?.jarak_saluran_meter != null ? `${selected.data.jarak_saluran_meter} meter` : "-"],
      ["Posisi pada Ruas", selected.data?.posisi_hulu_meter != null ? `${selected.data.posisi_hulu_meter} meter` : "-"],
    ]
  : [];

  return (
    <div className="building-page">
      <div className="page-heading">
        <div>
          <h1>Data Bangunan</h1>
          <p>Daftar aset bangunan pada Daerah Irigasi Kali Wening.</p>
        </div>
      </div>

      <section className="content-card building-page-card">
        <div className="building-toolbar">
          <div className="building-search">
            <Search size={18} />
            <input
              type="text"
              placeholder="Cari kode, nama bangunan, atau saluran..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select
            value={filterKondisi}
            onChange={(e) => setFilterKondisi(e.target.value)}
          >
            <option value="semua">Semua Kondisi</option>
            <option value="baik">Baik</option>
            <option value="rusak_ringan">Rusak Ringan</option>
            <option value="rusak_sedang">Rusak Sedang</option>
            <option value="rusak_berat">Rusak Berat</option>
          </select>

          <select
            value={filterJenis}
            onChange={(e) => setFilterJenis(e.target.value)}
          >
            <option value="semua">Semua Jenis</option>
            {daftarJenis.map((jenis) => (
              <option key={jenis} value={jenis}>
                {jenis}
              </option>
            ))}
          </select>
        </div>

        <div className="building-result-count">
          <Building2 size={17} />
          Menampilkan {hasilFilter.length} dari {aset.length} bangunan
        </div>

        {loading ? (
          <div className="empty-state">Memuat data bangunan...</div>
        ) : error ? (
          <div className="empty-state">{error}</div>
        ) : hasilFilter.length === 0 ? (
          <div className="empty-state">
            Tidak ada data yang sesuai dengan pencarian.
          </div>
        ) : (
          <div className="building-table-wrapper">
            <table className="building-table">
              <thead>
                <tr>
                  <th>No.</th>
                  <th>Kode Aset</th>
                  <th>Nomenklatur</th>
                  <th>Jenis</th>
                  <th>Saluran</th>
                  <th>Kondisi</th>
                  <th>Aksi</th>
                </tr>
              </thead>

              <tbody>
                {hasilFilter.map((item, index) => (
                  <tr key={item.kode_aset || index}>
                    <td>{index + 1}</td>
                    <td>
                      <strong>{item.kode_aset || "-"}</strong>
                    </td>
                    <td>{item.nomenklatur || "-"}</td>
                    <td>{item.jenis || "-"}</td>
                    <td>{item.nama_saluran || "-"}</td>
                    <td>
                      <span
                        className={`building-status ${item.kondisi || ""}`}
                      >
                        {labelKondisi[item.kondisi] || item.kondisi || "-"}
                      </span>
                    </td>
                    <td>
                      <button
                        className="building-detail-button"
                        onClick={() => handleDetail(item.kode_aset)}
                        title="Lihat detail"
                      >
                        <Eye size={16} />
                        Detail
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* MODAL DETAIL BANGUNAN */}
      {selected && (
        <div
          role="presentation"
          onClick={() => setSelected(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.65)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            padding: "20px",
            zIndex: 9999,
            overflowY: "auto",
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="detail-title"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "#ffffff",
              width: "100%",
              maxWidth: "650px",
              maxHeight: "90vh",
              overflowY: "auto",
              borderRadius: "16px",
              boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
              padding: "26px",
            }}
          >
            {/* HEADER */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                borderBottom: "1px solid #e2e8f0",
                paddingBottom: "18px",
                marginBottom: "22px",
              }}
            >
              <div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "9px",
                    color: "#168052",
                    marginBottom: "8px",
                  }}
                >
                  <Building2 size={22} />
                  <span style={{ fontSize: "13px", fontWeight: 600 }}>
                    INFORMASI ASET IRIGASI
                  </span>
                </div>

                <h2
                  id="detail-title"
                  style={{
                    margin: 0,
                    fontSize: "23px",
                    color: "#1e293b",
                  }}
                >
                  Detail Bangunan
                </h2>

                <p
                  style={{
                    margin: "6px 0 0",
                    color: "#64748b",
                    fontSize: "14px",
                  }}
                >
                  {selected.data.kode_aset || "-"}
                </p>
              </div>

              <button
                onClick={() => setSelected(null)}
                aria-label="Tutup detail"
                style={{
                  border: "none",
                  background: "#f1f5f9",
                  borderRadius: "8px",
                  padding: "9px",
                  cursor: "pointer",
                  display: "flex",
                }}
              >
                <X size={21} color="#475569" />
              </button>
            </div>

            {/* KONDISI BANGUNAN */}
            <div
              style={{
                background: "#f8fafc",
                padding: "18px",
                borderRadius: "12px",
                marginBottom: "22px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <div>
                <div
                  style={{
                    color: "#64748b",
                    fontSize: "13px",
                    marginBottom: "6px",
                  }}
                >
                  Kondisi Bangunan
                </div>

                <strong style={{ fontSize: "20px", color: "#1e293b" }}>
                  {labelKondisi[selected.data?.kondisi] ||
                    selected.data?.kondisi ||
                    "-"}
                </strong>
              </div>

              <span
                style={{
                  width: "13px",
                  height: "13px",
                  borderRadius: "50%",
                  background: warnaKondisi[selected.data?.kondisi] || "#94a3b8",
                }}
              />
            </div>

            {/* INFORMASI UMUM */}
            <div style={{ marginBottom: "24px" }}>
              <h3
                style={{
                  fontSize: "15px",
                  color: "#334155",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  marginBottom: "14px",
                }}
              >
                <Info size={18} />
                Informasi Umum
              </h3>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "12px",
                }}
              >
                {detailFields.slice(0, 4).map(([label, value]) => (
                  <div
                    key={label}
                    style={{
                      background: "#f8fafc",
                      padding: "13px",
                      borderRadius: "9px",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "12px",
                        color: "#64748b",
                        marginBottom: "6px",
                      }}
                    >
                      {label}
                    </div>
                    <strong
                      style={{
                        fontSize: "14px",
                        color: "#1e293b",
                        overflowWrap: "anywhere",
                      }}
                    >
                      {value ?? "-"}
                    </strong>
                  </div>
                ))}
              </div>
            </div>

            {/* INFORMASI LOKASI */}
            <div style={{ marginBottom: "24px" }}>
              <h3
                style={{
                  fontSize: "15px",
                  color: "#334155",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  marginBottom: "14px",
                }}
              >
                <MapPin size={18} />
                Informasi Lokasi
              </h3>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "12px",
                }}
              >
                {detailFields.slice(5).map(([label, value]) => (
                  <div
                    key={label}
                    style={{
                      background: "#f8fafc",
                      padding: "13px",
                      borderRadius: "9px",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "12px",
                        color: "#64748b",
                        marginBottom: "6px",
                      }}
                    >
                      {label}
                    </div>
                    <strong
                      style={{
                        fontSize: "14px",
                        color: "#1e293b",
                        overflowWrap: "anywhere",
                      }}
                    >
                      {value ?? "-"}
                    </strong>
                  </div>
                ))}
              </div>
            </div>

            {/* RIWAYAT */}
            {/* RIWAYAT PEMERIKSAAN */}
            <div
              style={{
                background: "#f8fafc",
                padding: "16px",
                borderRadius: "10px",
                marginBottom: "22px",
              }}
            >
              <h3
                style={{
                  fontSize: "15px",
                  color: "#334155",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  margin: "0 0 16px",
                }}
              >
                <Activity size={18} />
                Riwayat Pemeriksaan
              </h3>

              {selected.riwayat_laporan?.length > 0 ? (
                <div style={{ display: "grid", gap: "12px" }}>
                  {selected.riwayat_laporan.map((laporan) => (
                    <div
                      key={laporan.id_laporan}
                      style={{
                        background: "#ffffff",
                        border: "1px solid #e2e8f0",
                        borderRadius: "9px",
                        padding: "14px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          flexWrap: "wrap",
                          gap: "8px",
                          marginBottom: "10px",
                        }}
                      >
                        <strong style={{ color: "#1e293b", fontSize: "14px" }}>
                          {laporan.id_laporan}
                        </strong>

                        <span
                          style={{
                            padding: "4px 9px",
                            borderRadius: "20px",
                            fontSize: "12px",
                            fontWeight: 600,
                            background:
                              laporan.status === "aktif" ? "#dcfce7" : "#fee2e2",
                            color:
                              laporan.status === "aktif" ? "#166534" : "#991b1b",
                          }}
                        >
                          {laporan.status === "aktif" ? "Aktif" : laporan.status}
                        </span>
                      </div>

                      <div style={{ display: "grid", gap: "7px", fontSize: "13px" }}>
                        <div>
                          <span style={{ color: "#64748b" }}>Tanggal: </span>
                          <strong>{laporan.tanggal || "-"}</strong>
                        </div>

                        <div>
                          <span style={{ color: "#64748b" }}>Petugas: </span>
                          <strong>{laporan.petugas || "-"}</strong>
                        </div>

                        <div>
                          <span style={{ color: "#64748b" }}>Jenis Kerusakan: </span>
                          <strong>{laporan.jenis_kerusakan || "-"}</strong>
                        </div>

                        <div>
                          <span style={{ color: "#64748b" }}>Kondisi: </span>
                          <strong>
                            {labelKondisi[laporan.kondisi] || laporan.kondisi || "-"}
                          </strong>
                        </div>

                        <div>
                          <span style={{ color: "#64748b" }}>Keterangan: </span>
                          <span>{laporan.keterangan || "-"}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: "#64748b", fontSize: "13px", margin: 0 }}>
                  Belum tersedia riwayat pemeriksaan untuk bangunan ini.
                </p>
              )}
            </div>

            {/* FOOTER */}
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                onClick={() => setSelected(null)}
                style={{
                  background: "#168052",
                  color: "#ffffff",
                  border: "none",
                  padding: "11px 24px",
                  borderRadius: "8px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}