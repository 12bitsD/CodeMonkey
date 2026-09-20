import { notesApi, tokenManager } from './api';
import { buildApiUrl } from '../config/api';

const authHeaders = () => {
  const token = tokenManager.get();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const normalizeApiLanguage = (language) =>
  language === 'zh-CN' ? 'zh-CN' : 'en-US';

async function apiError(response, fallbackMessage) {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // Some upstream failures return an empty or non-JSON response.
  }
  const detail = payload?.detail || payload?.error || payload;
  const message = typeof detail === 'string'
    ? detail
    : detail?.message || fallbackMessage;
  const error = new Error(message);
  error.code = detail?.code || 'REQUEST_FAILED';
  error.status = response.status;
  return error;
}

export const deepLearnApi = {
  createSession: async ({ nodeId, planId, language = null }) => {
    const res = await fetch(buildApiUrl('/deep-learn/sessions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        node_id: nodeId,
        plan_id: planId,
        ...(language ? { language: normalizeApiLanguage(language) } : {}),
      }),
    });
    if (!res.ok) throw new Error(`createSession failed: ${res.status}`);
    return res.json();
  },

  getSession: async (sessionId) => {
    const res = await fetch(buildApiUrl(`/deep-learn/sessions/${sessionId}`), {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`getSession failed: ${res.status}`);
    return res.json();
  },

  initialize: (sessionId, language = null) => fetch(
    buildApiUrl(`/deep-learn/sessions/${sessionId}/initialize${language ? `?language=${encodeURIComponent(normalizeApiLanguage(language))}` : ''}`),
    { method: 'POST', headers: authHeaders() },
  ),

  sendMessage: (sessionId, content, language = null) => fetch(
    buildApiUrl(`/deep-learn/sessions/${sessionId}/message`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        content,
        ...(language ? { language: normalizeApiLanguage(language) } : {}),
      }),
    },
  ),

  sendCommand: (sessionId, command, language = null) => fetch(
    buildApiUrl(`/deep-learn/sessions/${sessionId}/command`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        command,
        ...(language ? { language: normalizeApiLanguage(language) } : {}),
      }),
    },
  ),

  generateIllustration: async (sessionId, offerId) => {
    const res = await fetch(buildApiUrl(`/deep-learn/sessions/${sessionId}/illustrations`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ offer_id: offerId }),
    });
    if (!res.ok) {
      throw await apiError(res, `generateIllustration failed: ${res.status}`);
    }
    return res.json();
  },
};

export const createNoteFromDeepLearn = async ({ planId, nodeId, content }) => {
  return notesApi.create(planId, nodeId, content);
};
