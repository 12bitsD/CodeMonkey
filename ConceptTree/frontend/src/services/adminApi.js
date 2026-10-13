import { ApiError, fetchApi } from "./api";

export const ADMIN_SESSION_EXPIRED_EVENT = "concept-tree-admin-session-expired";

const buildQuery = (params = {}) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  });
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
};

const adminRequest = async (endpoint, options = {}, notifyOnUnauthorized = true) => {
  try {
    return await fetchApi(`/admin${endpoint}`, {
      ...options,
      credentials: "include",
      preserveSessionOnUnauthorized: true,
    });
  } catch (error) {
    if (
      notifyOnUnauthorized &&
      error instanceof ApiError &&
      error.status === 401 &&
      typeof window !== "undefined"
    ) {
      window.dispatchEvent(new CustomEvent(ADMIN_SESSION_EXPIRED_EVENT));
    }
    throw error;
  }
};

export const adminApi = {
  me: () => adminRequest("/me", { suppressErrorLog: true }, false),

  elevate: (password) =>
    adminRequest(
      "/auth/session",
      { method: "POST", body: JSON.stringify({ password }) },
      false,
    ),

  logout: () => adminRequest("/auth/session", { method: "DELETE" }, false),

  overview: (range) => adminRequest(`/overview${buildQuery(range)}`),
  timeseries: (range) => adminRequest(`/timeseries${buildQuery(range)}`),
  users: (params) => adminRequest(`/users${buildQuery(params)}`),
  user: (userId) => adminRequest(`/users/${encodeURIComponent(userId)}`),
  sessions: ({ userId, ...params } = {}) =>
    adminRequest(`/sessions${buildQuery({ ...params, user_id: userId })}`),
  session: (sessionId) =>
    adminRequest(`/sessions/${encodeURIComponent(sessionId)}`),
  trace: (sessionId, params) =>
    adminRequest(
      `/sessions/${encodeURIComponent(sessionId)}/trace${buildQuery(params)}`,
    ),
  aiUsage: (range) => adminRequest(`/ai-usage${buildQuery(range)}`),
  systemHealth: () => adminRequest("/system-health"),
};

export { buildQuery };
