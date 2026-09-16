import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

const REFRESH_KEY = "forge.refresh";
let accessToken: string | null = null;

export const tokens = {
  getAccess: () => accessToken,
  setAccess: (t: string | null) => {
    accessToken = t;
  },
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  setRefresh: (t: string | null) => {
    if (t) localStorage.setItem(REFRESH_KEY, t);
    else localStorage.removeItem(REFRESH_KEY);
  },
  clear: () => {
    accessToken = null;
    localStorage.removeItem(REFRESH_KEY);
  },
};

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const t = tokens.getAccess();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

export async function refreshAccess(): Promise<string | null> {
  const refresh = tokens.getRefresh();
  if (!refresh) return null;
  refreshing ??= axios
    .post(`${API_URL}/auth/token/refresh/`, { refresh })
    .then((res) => {
      tokens.setAccess(res.data.access);
      if (res.data.refresh) tokens.setRefresh(res.data.refresh);
      return res.data.access as string;
    })
    .catch(() => {
      tokens.clear();
      return null;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true;
      const t = await refreshAccess();
      if (t) {
        original.headers.Authorization = `Bearer ${t}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  },
);

export type ApiError = { detail: string; code: string; errors: Record<string, unknown> };

function flatten(value: unknown): string {
  if (Array.isArray(value)) return value.map(flatten).join(" ");
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([k, v]) => `${k}: ${flatten(v)}`)
      .join("; ");
  }
  return String(value);
}

export function errorMessage(err: unknown): string {
  const data = (err as AxiosError<ApiError>)?.response?.data;
  if (!data) return `Cannot reach the API at ${API_URL}. Is the backend running?`;
  const fields = flatten(data.errors ?? {});
  return fields ? `${data.detail} ${fields}` : data.detail;
}
