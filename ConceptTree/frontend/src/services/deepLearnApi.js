import { notesApi, tokenManager } from './api';
import { buildApiUrl } from '../config/api';

const authHeaders = () => {
  const token = tokenManager.get();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const deepLearnApi = {
  createSession: async ({ nodeId, planId }) => {
    const res = await fetch(buildApiUrl('/deep-learn/sessions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ node_id: nodeId, plan_id: planId }),
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

  initialize: (sessionId) => fetch(
    buildApiUrl(`/deep-learn/sessions/${sessionId}/initialize`),
    { method: 'POST', headers: authHeaders() },
  ),

  sendMessage: (sessionId, content) => fetch(
    buildApiUrl(`/deep-learn/sessions/${sessionId}/message`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ content }),
    },
  ),

  sendCommand: (sessionId, command) => fetch(
    buildApiUrl(`/deep-learn/sessions/${sessionId}/command`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ command }),
    },
  ),
};

export const createNoteFromDeepLearn = async ({ planId, nodeId, content }) => {
  return notesApi.create(planId, nodeId, content);
};
