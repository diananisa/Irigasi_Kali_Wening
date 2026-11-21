import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export const getHealth = () => api.get("/health");
export const getVersi = () => api.get("/versi");

export const getAset = (params = {}) => api.get("/aset", { params });
export const getSaluran = () => api.get("/saluran");
export const getPetak = () => api.get("/petak");

export const getDetailAset = (kodeAset) =>
  api.get(`/aset/${encodeURIComponent(kodeAset)}`);

export const getDampakAset = (kodeAset) =>
  api.get(`/aset/${encodeURIComponent(kodeAset)}/dampak`);

export const getRekapSaluran = () => api.get("/rekap/saluran");
export const getPrioritas = () => api.get("/prioritas");
export const getKualitasData = () => api.get("/kualitas-data");

export const imporLaporanSusulan = (file) => {
  const formData = new FormData();
  formData.append("file", file);

  return api.post("/impor/susulan", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export default api;