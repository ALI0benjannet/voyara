import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import { env } from "@voyara/api/env";
import { endpoints } from "@voyara/api/endpoints";
import { authStore } from "@voyara/auth/stores/auth.store";

export const api = axios.create({
  baseURL: env.VITE_API_URL,
  timeout: 20_000,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

/* ---------- Requête : injection du JWT + langue ---------- */
api.interceptors.request.use((config) => {
  const token = authStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  config.headers["Accept-Language"] = localStorage.getItem("i18nextLng") ?? "fr";
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }
  return config;
});

/* ---------- Réponse : refresh automatique sur 401 ---------- */
type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

let isRefreshing = false;
let waiters: Array<(token: string | null) => void> = [];

const notifyWaiters = (token: string | null) => {
  waiters.forEach((resolve) => resolve(token));
  waiters = [];
};

/* Branché par le AuthProvider pour déconnecter proprement. */
let onSessionExpired: () => void = () => {};
export const setSessionExpiredHandler = (fn: () => void) => {
  onSessionExpired = fn;
};

const NO_REFRESH_PATHS = [
  endpoints.auth.login,
  endpoints.auth.refresh,
  endpoints.auth.register,
];

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    const status = error.response?.status;

    const shouldRefresh =
      status === 401 &&
      !!original &&
      !original._retry &&
      !NO_REFRESH_PATHS.some((path) => original.url?.includes(path));

    if (!shouldRefresh || !original) return Promise.reject(error);

    original._retry = true;

    if (isRefreshing) {
      const token = await new Promise<string | null>((r) => waiters.push(r));
      if (!token) return Promise.reject(error);
      original.headers.Authorization = `Bearer ${token}`;
      return api(original);
    }

    isRefreshing = true;
    try {
      const refreshToken = authStore.getState().refreshToken;
      if (!refreshToken) throw error;

      // Instance nue : évite une boucle infinie d'intercepteurs
      const { data } = await axios.post(
        `${env.VITE_API_URL}${endpoints.auth.refresh}`,
        { refresh_token: refreshToken },
        { withCredentials: true },
      );

      authStore.getState().setTokens(data.access_token, data.refresh_token);
      notifyWaiters(data.access_token);
      original.headers.Authorization = `Bearer ${data.access_token}`;
      return api(original);
    } catch (refreshError) {
      notifyWaiters(null);
      authStore.getState().logout();
      onSessionExpired();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);