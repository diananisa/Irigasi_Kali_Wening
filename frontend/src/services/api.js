import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export const getHealth = () => api.get("/health");
export const getAset = (params = {}) => api.get("/aset", { params });
export const getSaluran = () => api.get("/saluran");
export const getPetak = () => api.get("/petak");
export const getDetailAset = (kodeAset) => api.get(`/aset/${kodeAset}`);

export default api;
