import { createEmptyUserProfile } from "../types";
import { buildApiUrl } from "../config/api";

const TOKEN_KEY = "concept_tree_token";
export const AUTH_EXPIRED_EVENT = "concept-tree-auth-expired";

export const tokenManager = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  remove: () => localStorage.removeItem(TOKEN_KEY),
};

const notifyAuthExpired = () => {
  tokenManager.remove();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
  }
};

const fetchApi = async (endpoint, options = {}) => {
  try {
    const headers = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    const token = tokenManager.get();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(buildApiUrl(endpoint), {
      headers,
      ...options,
    });
    if (res.status === 401) {
      notifyAuthExpired();
    }
    const raw = await res.text();
    let json = null;

    if (raw) {
      try {
        json = JSON.parse(raw);
      } catch {
        throw new Error(`Invalid JSON response (${res.status})`);
      }
    }

    if (!json) {
      throw new Error(`Empty response from server (${res.status})`);
    }

    if (!json.success) {
      throw new Error(json.error?.message || "API Error");
    }
    return json.data;
  } catch (err) {
    console.error(`API Call Failed: ${endpoint}`, err);
    throw err;
  }
};

// edges 字段映射：后端 {from_node, to_node} ↔ 前端 {from, to}
export const mapEdgesFromBackend = (edges) =>
  (edges || []).map((e) => {
    const { from_node, to_node, ...rest } = e;
    return {
      ...rest,
      from: from_node || e.from,
      to: to_node || e.to,
    };
  });

export const mapEdgesToBackend = (edges) =>
  (edges || []).map((e) => {
    const { from, to, ...rest } = e;
    return {
      ...rest,
      from_node: from || e.from_node,
      to_node: to || e.to_node,
    };
  });

// ─── 认证 API (Real Backend) ───

export const authApi = {
  register: async (email, password) => {
    return await fetchApi("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  login: async (email, password) => {
    return await fetchApi("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  logout: async () => {
    await fetchApi("/auth/logout", { method: "POST" }).catch(() => {});
  },
};

// ─── 用户画像 API (Real Backend) ───

export const userProfileApi = {
  get: async () => {
    try {
      return await fetchApi("/user/profile");
    } catch (error) {
      console.warn(
        "Failed to fetch profile from backend, using empty profile",
        error,
      );
      return createEmptyUserProfile();
    }
  },

  update: async (profile) => {
    return await fetchApi("/user/profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    });
  },
};

// ─── 学习计划 API (Real Backend) ───

export const plansApi = {
  list: async () => {
    try {
      return await fetchApi("/plans");
    } catch (e) {
      console.warn("Backend unavailable, falling back to empty list", e);
      return [];
    }
  },

  create: async ({ title, originalInput, targetNodeId, nodes, edges, learning_purpose = "apply" }) => {
    return await fetchApi("/plans", {
      method: "POST",
      body: JSON.stringify({
        title,
        originalInput,
        targetNodeId,
        nodes,
        edges: mapEdgesToBackend(edges),
        learning_purpose,
      }),
    });
  },

  update: async (id, data) => {
    const updateData = { ...data };
    if (updateData.edges) {
      updateData.edges = mapEdgesToBackend(updateData.edges);
    }
    
    return await fetchApi(`/plans/${id}`, {
      method: "PUT",
      body: JSON.stringify(updateData),
    });
  },

  archive: async (id) => {
    return await fetchApi(`/plans/${id}/archive`, {
      method: "PUT",
    });
  },

  restore: async (id) => {
    return await fetchApi(`/plans/${id}/restore`, {
      method: "PUT",
    });
  },

  delete: async (id) => {
    return await fetchApi(`/plans/${id}`, {
      method: "DELETE",
    });
  },
};

// ─── 图谱 API (Real Backend) ───

const mapUserProfileToBackground = (profile) => {
  if (!profile) return null;
  return {
    occupation: profile.occupation || "",
    education: profile.education || "",
    programmingLevel: profile.programmingLevel || "",
    mathLevel: profile.mathLevel || "",
    abilities: profile.abilities || [],
    masteredKnowledge: profile.masteredKnowledge || [],
  };
};

export const graphApi = {
  generate: async (
    input,
    userProfileOrInterpretation = null,
    userProfile = null,
    learningPurpose = "apply",
    onProgress = null,
  ) => {
    // 检测是否是旧调用（第二个参数是 profile）还是新调用（第二个是 interpretation）
    let interpretation, profile;
    if (
      userProfileOrInterpretation &&
      typeof userProfileOrInterpretation === "object"
    ) {
      // 旧调用：第二个参数是 profile
      interpretation = input;
      profile = userProfileOrInterpretation;
    } else {
      // 新调用：第二个参数是 interpretation
      interpretation = userProfileOrInterpretation || input;
      profile = userProfile;
    }

    const body = { input, interpretation, learning_purpose: learningPurpose };
    const userBackground = mapUserProfileToBackground(profile);
    if (userBackground) {
      body.userBackground = userBackground;
    }

    // F5: SSE streaming client — POST + ReadableStream
    const token = tokenManager.get();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(buildApiUrl("/ai/generate-graph"), {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (res.status === 401) {
      notifyAuthExpired();
    }
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: Failed to generate graph`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let meta = null;
    const nodes = [];
    let edges = [];

    outer: for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop(); // keep last incomplete line

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;
        const event = JSON.parse(jsonStr);

        if (event.type === "error") {
          throw new Error(event.error?.message || "Generation failed");
        } else if (event.type === "meta") {
          meta = event;
          if (onProgress) onProgress({ type: "meta", ...event });
        } else if (event.type === "node") {
          nodes.push(event.node);
          if (onProgress)
            onProgress({
              type: "node",
              node: event.node,
              received: nodes.length,
              total: meta?.totalNodes,
            });
        } else if (event.type === "edges") {
          edges = event.edges;
        } else if (event.type === "done") {
          break outer;
        }
      }
    }

    return {
      interpretation: meta?.interpretation,
      targetNodeId: meta?.targetNodeId,
      nodes,
      edges: mapEdgesFromBackend(edges),
    };
  },

  get: async (planId) => {
    const result = await fetchApi(`/plans/${planId}/graph`);
    return {
      ...result,
      edges: mapEdgesFromBackend(result.edges),
    };
  },

  updateNodeStatus: async (planId, nodeId, status) => {
    return await fetchApi(`/plans/${planId}/nodes/${nodeId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
  },

  updateNodePosition: async (planId, nodeId, x, y) => {
    return await fetchApi(`/plans/${planId}/nodes/${nodeId}/position`, {
      method: "PUT",
      body: JSON.stringify({ x, y }),
    });
  },

  searchNodeResources: async (planId, nodeId, query = null) => {
    return await fetchApi(`/plans/${planId}/nodes/${nodeId}/search-resources`, {
      method: "POST",
      body: JSON.stringify(query ? { query } : {}),
    });
  },

  applyChanges: async (planId, { keep, remove, add, newTitle }) => {
    return await fetchApi(`/plans/${planId}/apply-changes`, {
      method: "POST",
      body: JSON.stringify({ keep, remove, add, newTitle }),
    });
  },
};

// ─── 笔记 API (Real Backend) ───

export const notesApi = {
  list: async (planId = null) => {
    const params = planId ? `?planId=${planId}` : "";
    return await fetchApi(`/notes${params}`);
  },

  create: async (planId, nodeId, content) => {
    return await fetchApi("/notes", {
      method: "POST",
      body: JSON.stringify({ planId, nodeId, content }),
    });
  },

  update: async (noteId, content) => {
    return await fetchApi(`/notes/${noteId}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    });
  },

  delete: async (noteId) => {
    return await fetchApi(`/notes/${noteId}`, {
      method: "DELETE",
    });
  },
};

// ─── AI API (Real Backend) ───

export const aiApi = {
  parseGoal: async (input, userProfile = null) => {
    const body = { input };
    const userBackground = mapUserProfileToBackground(userProfile);
    if (userBackground) {
      body.userBackground = userBackground;
    }

    return await fetchApi("/ai/parse-goal", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  clarifyGoal: async (originalGoal, newGoal, planId = null) => {
    return await fetchApi("/ai/clarify-goal", {
      method: "POST",
      body: JSON.stringify({ originalGoal, newGoal, ...(planId ? { planId } : {}) }),
    });
  },

  recommendNext: async (planId) => {
    return await fetchApi("/ai/recommend-next", {
      method: "POST",
      body: JSON.stringify({ planId }),
    });
  },

  /**
   * F7: Stream AI explanation for a what-item topic.
   * Calls onChunk(text) for each chunk, returns full text when done.
   */
  explainTopic: async (nodeId, topicIndex, topicText, nodeContext, onChunk) => {
    const token = tokenManager.get();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(buildApiUrl("/ai/explain-topic"), {
      method: "POST",
      headers,
      body: JSON.stringify({ nodeId, topicIndex, topicText, nodeContext }),
    });

    if (res.status === 401) {
      notifyAuthExpired();
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}: explain-topic failed`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let fullText = "";

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;
        const event = JSON.parse(jsonStr);
        if (event.type === "chunk") {
          fullText += event.text;
          if (onChunk) onChunk(event.text);
        } else if (event.type === "error") {
          console.error("[explainTopic SSE] error event:", event.error);
          throw new Error(event.error?.message || "explain-topic error");
        } else if (event.type === "done") {
          // Stream complete
        }
      }
    }
    return fullText;
  },

  /**
   * F4: Stream AI chat response.
   * messages: [{role, content}], nodeContext: {nodeName, planTitle, why}
   * Calls onChunk(text) for each chunk, returns full text when done.
   */
  chatStream: async (messages, nodeContext, onChunkOrOptions) => {
    const options =
      typeof onChunkOrOptions === "function"
        ? { onChunk: onChunkOrOptions }
        : (onChunkOrOptions || {});
    const {
      enableWebSearch = false,
      onChunk,
      onSources,
      onSearchStatus,
    } = options;

    const token = tokenManager.get();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(buildApiUrl("/ai/chat"), {
      method: "POST",
      headers,
      body: JSON.stringify({ messages, nodeContext, enableWebSearch }),
    });

    if (res.status === 401) {
      notifyAuthExpired();
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}: chat failed`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let fullText = "";

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;
        const event = JSON.parse(jsonStr);
        if (event.type === "chunk") {
          fullText += event.text;
          if (onChunk) onChunk(event.text);
        } else if (event.type === "sources") {
          if (onSources) onSources(event.sources || []);
        } else if (event.type === "search_status") {
          if (onSearchStatus) onSearchStatus(event.status || null);
        } else if (event.type === "error") {
          throw new Error(event.error?.message || "chat error");
        }
      }
    }
    return fullText;
  },
};

// ─── 统计 API (Real Backend) ───

export const statsApi = {
  getOverview: async () => {
    return await fetchApi("/stats/overview");
  },

  getDistribution: async () => {
    return await fetchApi("/stats/distribution");
  },
};
