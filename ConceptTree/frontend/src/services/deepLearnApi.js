import { notesApi, tokenManager } from './api';
import { buildApiUrl } from '../config/api';

const authHeaders = () => {
  const token = tokenManager.get();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const normalizeApiLanguage = (language) =>
  language === 'zh-CN' ? 'zh-CN' : 'en-US';

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
};

export const createNoteFromDeepLearn = async ({ planId, nodeId, content }) => {
  return notesApi.create(planId, nodeId, content);
};
