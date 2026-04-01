import axios, { AxiosError } from "axios";
import { toast } from "sonner";

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 500;

// Status codes that are safe to retry (transient server errors / network issues)
const RETRYABLE_STATUS = new Set([408, 429, 500, 502, 503, 504]);

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// In-memory token store — not persisted to localStorage, reducing XSS attack surface.
// Refresh token lives in httpOnly cookie (set by backend), so page reload
// triggers a silent refresh via /auth/refresh.
let _accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  _accessToken = token;
  // Keep localStorage in sync for backward compat (existing tabs).
  // TODO: remove localStorage usage entirely once all entry points migrate.
  if (token) {
    localStorage.setItem("access_token", token);
  } else {
    localStorage.removeItem("access_token");
  }
}

export function getAccessToken(): string | null {
  // Hydrate from localStorage on first call (page reload)
  if (!_accessToken) {
    _accessToken = localStorage.getItem("access_token");
  }
  return _accessToken;
}

export function clearAccessToken() {
  _accessToken = null;
  localStorage.removeItem("access_token");
}

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  timeout: 30_000,
});

// Request interceptor: attach access token from memory
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: retry with exponential backoff, then refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config;
    if (!original) return Promise.reject(error);

    // --- Exponential backoff retry for transient errors ---
    const retryCount: number =
      (original as unknown as Record<string, unknown>).__retryCount as number ?? 0;
    const status = error.response?.status;
    const isNetworkError = !error.response; // timeout, DNS, connection refused

    if (
      retryCount < MAX_RETRIES &&
      (isNetworkError || (status && RETRYABLE_STATUS.has(status)))
    ) {
      (original as unknown as Record<string, unknown>).__retryCount = retryCount + 1;
      const waitMs = BASE_DELAY_MS * Math.pow(2, retryCount); // 500, 1000, 2000
      const jitter = Math.random() * waitMs * 0.2; // ±20% jitter
      await delay(waitMs + jitter);
      return api(original);
    }

    // --- Token refresh on 401 ---
    if (
      status === 401 &&
      !(original as unknown as Record<string, unknown>)._retry &&
      !original.url?.includes("/auth/")
    ) {
      (original as unknown as Record<string, unknown>)._retry = true;
      try {
        const { data } = await axios.post(
          "/api/v1/auth/refresh",
          {},
          { withCredentials: true }
        );
        setAccessToken(data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        clearAccessToken();
        window.location.href = "/login";
        return Promise.reject(error);
      }
    }

    // --- Toast for non-401 errors (after all retries exhausted) ---
    if (status && status !== 401) {
      const message =
        (error.response?.data as { detail?: string })?.detail ||
        `Request failed (${status})`;
      toast.error(message);
    } else if (isNetworkError) {
      toast.error("Network error. Please check your connection.");
    }

    return Promise.reject(error);
  }
);

export default api;
