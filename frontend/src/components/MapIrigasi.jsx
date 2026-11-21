import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Marker,
  Popup,
} from "react-leaflet";
import L from "leaflet";

import "leaflet/dist/leaflet.css";

import {
  getAset,
  getSaluran,
  getPetak,
  getDampakAset,
} from "../services/api";

// Warna berdasarkan kondisi fisik
const warnaKondisi = {
  baik: "#16a34a",
  rusak_ringan: "#eab308",
  rusak_sedang: "#f97316",
  rusak_berat: "#dc2626",
};

// Simbol berdasarkan jenis bangunan
const simbolBangunan = {
  bendung: "■",
  bangunan_bagi: "+",
  bangunan_bagi_sadap: "⊕",
  bangunan_sadap: "▼",
  bangunan_pelengkap: "◆",
};

const labelJenis = {
  bendung: "Bendung",
  bangunan_bagi: "Bangunan Bagi",
  bangunan_bagi_sadap: "Bangunan Bagi Sadap",
  bangunan_sadap: "Bangunan Sadap",
  bangunan_pelengkap: "Bangunan Pelengkap",
};

const labelKondisi = {
  baik: "Baik",
  rusak_ringan: "Rusak Ringan",
  rusak_sedang: "Rusak Sedang",
  rusak_berat: "Rusak Berat",
};

// Membuat ikon Leaflet berdasarkan jenis dan kondisi bangunan
const buatIkonBangunan = (jenis, kondisi) => {
  const simbol = simbolBangunan[jenis] || "●";
  const warna = warnaKondisi[kondisi] || "#64748b";

  return L.divIcon({
    className: "building-map-icon",
    html: `
      <div style="
        width: 25px;
        height: 25px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: ${warna};
        font-size: 21px;
        font-weight: 900;
        text-shadow:
          -1px -1px 0 white,
          1px -1px 0 white,
          -1px 1px 0 white,
          1px 1px 0 white;
      ">${simbol}</div>
    `,
    iconSize: [25, 25],
    iconAnchor: [12, 12],
  });
};

export default function MapIrigasi() {
  const [saluran, setSaluran] = useState(null);
  const [petak, setPetak] = useState(null);
  const [aset, setAset] = useState([]);
  const [dampak, setDampak] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getSaluran(), getPetak(), getAset()])
      .then(([resSaluran, resPetak, resAset]) => {
        setSaluran(resSaluran.data);
        setPetak(resPetak.data);
        setAset(resAset.data.data || []);
      })
      .catch((err) => {
        console.error("Gagal memuat peta:", err);
        setError("Gagal memuat data peta dari server.");
      })
      .finally(() => setLoading(false));
  }, []);

  const muatDampak = async (kodeAset) => {
    if (dampak[kodeAset]) return;

    try {
      const response = await getDampakAset(kodeAset);

      setDampak((sebelumnya) => ({
        ...sebelumnya,
        [kodeAset]: response.data,
      }));
    } catch (err) {
      console.error("Gagal mengambil dampak aset:", err);
    }
  };

  // Warna garis saluran berdasarkan kondisi
  const styleSaluran = (feature) => {
    const kondisi = feature.properties?.kondisi;

    return {
      color: warnaKondisi[kondisi] || "#64748b",
      weight: 4,
      opacity: 0.9,
    };
  };

  // Warna petak berdasarkan status anomali
  const stylePetak = (feature) => ({
    color: feature.properties?.anomali ? "#dc2626" : "#65a30d",
    weight: 1,
    fillColor: feature.properties?.anomali ? "#fca5a5" : "#a3e635",
    fillOpacity: 0.18,
  });

  if (loading) {
    return (
      <div className="map-placeholder">
        Memuat peta jaringan irigasi...
      </div>
    );
  }

  if (error) {
    return <div className="map-placeholder">{error}</div>;
  }

  return (
    <div className="map-wrapper">
      <div className="map-legend">
        <span>
          <i className="legend-line baik" />
          Saluran Baik
        </span>

        <span>
          <i className="legend-line rusak_ringan" />
          Rusak Ringan
        </span>

        <span>
          <i className="legend-line rusak_sedang" />
          Rusak Sedang
        </span>

        <span>
          <i className="legend-line rusak_berat" />
          Rusak Berat
        </span>

        <span>
          <i className="legend-area" />
          Petak Tersier
        </span>
      </div>

      <div className="map-legend">
        {Object.entries(simbolBangunan).map(([jenis, simbol]) => (
          <span key={jenis}>
            <i className={`legend-symbol ${jenis}`}>
              {simbol}
            </i>
            {labelJenis[jenis]}
          </span>
        ))}
      </div>

      <MapContainer
        center={[-7.63, 110.40]}
        zoom={13}
        scrollWheelZoom={true}
        className="irigasi-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Petak tersier */}
        {petak && (
          <GeoJSON
            data={petak}
            style={stylePetak}
            onEachFeature={(feature, layer) => {
              const p = feature.properties || {};

              const popup = document.createElement("div");
              popup.innerHTML = `
                <strong>Petak ${p.kode_petak || "-"}</strong>
                <br/>Luas baku: ${p.luas_baku_ha ?? "-"} ha
                <br/>Luas geometri: ${p.luas_geometri_ha ?? "-"} ha
                <br/>Luas dampak: ${p.luas_dampak_ha ?? "-"} ha
                <br/>Status validasi: ${p.status_validasi || "-"}
                <br/>Anomali: ${p.anomali ? "Ya" : "Tidak"}
              `;

              layer.bindPopup(popup);
            }}
          />
        )}

        {/* Saluran irigasi */}
        {saluran && (
          <GeoJSON
            data={saluran}
            style={styleSaluran}
            onEachFeature={(feature, layer) => {
              const p = feature.properties || {};

              layer.bindPopup(`
                <strong>${p.id_ruas || "-"}</strong>
                <br/>${p.nama_saluran || "-"}
                <br/>Tingkat: ${p.tingkat || "-"}
                <br/>Kondisi: ${labelKondisi[p.kondisi] || p.kondisi || "-"}
              `);
            }}
          />
        )}

        {/* Bangunan irigasi */}
        {aset.map((item) => {
          if (
            typeof item.x !== "number" ||
            typeof item.y !== "number" ||
            !Number.isFinite(item.x) ||
            !Number.isFinite(item.y)
          ) {
            return null;
          }

          return (
            <Marker
              key={item.kode_aset}
              position={[item.y, item.x]}
              icon={buatIkonBangunan(item.jenis, item.kondisi)}
              eventHandlers={{
                click: () => muatDampak(item.kode_aset),
              }}
            >
              <Popup>
                <div style={{ minWidth: "190px" }}>
                  <strong>{item.kode_aset}</strong>
                  <br />
                  {item.nomenklatur || "-"}
                  <br />
                  Jenis: {labelJenis[item.jenis] || item.jenis || "-"}
                  <br />
                  Saluran: {item.nama_saluran || "-"}
                  <br />
                  Kondisi: {labelKondisi[item.kondisi] || item.kondisi || "-"}

                  <hr />

                  <strong>Dampak Petak Tersier</strong>
                  <br />

                  {dampak[item.kode_aset]?.dampak ? (
                    <>
                      Jumlah petak:{" "}
                      {dampak[item.kode_aset].dampak.jumlah_petak_terdampak}
                      <br />
                      Luas terdampak:{" "}
                      {Number(
                        dampak[item.kode_aset].dampak.luas_terdampak_ha || 0
                      ).toLocaleString("id-ID", {
                        maximumFractionDigits: 2,
                      })}{" "}
                      ha
                    </>
                  ) : (
                    "Memuat informasi dampak..."
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}