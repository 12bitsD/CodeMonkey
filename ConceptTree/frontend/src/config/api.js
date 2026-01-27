const rawBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api';
const normalizedBaseUrl = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl;

export const API_BASE_URL = normalizedBaseUrl;

export const buildApiUrl = (endpoint = '') => {
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${normalizedEndpoint}`;
};
