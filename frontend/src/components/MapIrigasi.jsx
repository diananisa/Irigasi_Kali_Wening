import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Popup,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import { getAset, getSaluran, getPetak } from "../services/api";

export default function MapIrigasi() {
  const [saluran, setSaluran] = useState(null);
  const [petak, setPetak] = useState(null);
  const [aset, setAset] = useState([]);
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

  const stylePetak = (feature) => ({
    color: feature.properties?.anomali ? "#dc2626" : "#65a30d",
    weight: 1,
    fillColor: feature.properties?.anomali ? "#fca5a5" : "#a3e635",
    fillOpacity: 0.18,
  });

  const styleSaluran = (feature) => {
    const tingkat = feature.properties?.tingkat;

    return {
      color:
        tingkat === "primer"
          ? "#2563eb"
          : tingkat === "sekunder"
            ? "#0891b2"
            : "#0d9488",
      weight: tingkat === "primer" ? 5 : 3,
      opacity: 0.9,
    };
  };

  if (loading) {
    return <div className="map-placeholder">Memuat peta jaringan irigasi...</div>;
  }

  if (error) {
    return <div className="map-placeholder">{error}</div>;
  }

  return (
    <div className="map-wrapper">
      <div className="map-legend">
        <span><i className="legend-dot building" /> Bangunan</span>
        <span><i className="legend-line primary" /> Saluran primer</span>
        <span><i className="legend-line secondary" /> Saluran sekunder</span>
        <span><i className="legend-area" /> Petak tersier</span>
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

        {petak && (
          <GeoJSON
            data={petak}
            style={stylePetak}
            onEachFeature={(feature, layer) => {
              const p = feature.properties;
              layer.bindPopup(
                `<b>Petak ${p.kode_petak || "-"}</b><br/>
                Luas baku: ${p.luas_baku_ha ?? "-"} ha<br/>
                Luas geometri: ${p.luas_geometri_ha ?? "-"} ha<br/>
                Status: ${p.status_validasi || "-"}`
              );
            }}
          />
        )}

        {saluran && (
          <GeoJSON
            data={saluran}
            style={styleSaluran}
            onEachFeature={(feature, layer) => {
              const p = feature.properties;
              layer.bindPopup(
                `<b>${p.id_ruas || "-"}</b><br/>
                ${p.nama_saluran || "-"}<br/>
                Tingkat: ${p.tingkat || "-"}<br/>
                Kondisi: ${p.kondisi || "-"}`
              );
            }}
          />
        )}

        {aset.map((item) => {
          if (
            typeof item.x !== "number" ||
            typeof item.y !== "number"
          ) {
            return null;
          }

          const warna = {
            baik: "#16a34a",
            rusak_ringan: "#eab308",
            rusak_sedang: "#f97316",
            rusak_berat: "#dc2626",
          };

          return (
            <CircleMarker
              key={item.kode_aset}
              center={[item.y, item.x]}
              radius={6}
              pathOptions={{
                color: "#ffffff",
                weight: 1.5,
                fillColor: warna[item.kondisi] || "#64748b",
                fillOpacity: 1,
              }}
            >
              <Popup>
                <strong>{item.kode_aset}</strong>
                <br />
                {item.nomenklatur || "-"}
                <br />
                Jenis: {item.jenis || "-"}
                <br />
                Saluran: {item.nama_saluran || "-"}
                <br />
                Kondisi: {item.kondisi || "-"}
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
