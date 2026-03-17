import { createEmptyUserProfile } from "../types";
import { buildApiUrl } from "../config/api";

const TOKEN_KEY = "concept_tree_token";

export const tokenManager = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  remove: () => localStorage.removeItem(TOKEN_KEY),
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
    const json = await res.json();
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
const mapEdgesFromBackend = (edges) =>
  (edges || []).map((e) => ({
    from: e.from_node || e.from,
    to: e.to_node || e.to,
  }));

const mapEdgesToBackend = (edges) =>
  (edges || []).map((e) => ({
    from_node: e.from_node || e.from,
    to_node: e.to_node || e.to,
  }));

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
    try {
      await fetchApi("/auth/logout", { method: "POST" });
    } finally {
      tokenManager.remove();
    }
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

  create: async ({ title, originalInput, targetNodeId, nodes, edges }) => {
    return await fetchApi("/plans", {
      method: "POST",
      body: JSON.stringify({
        title,
        originalInput,
        targetNodeId,
        nodes,
        edges: mapEdgesToBackend(edges),
      }),
    });
  },

  update: async (id, data) => {
    return await fetchApi(`/plans/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
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

export const graphApi = {
  generate: async (input) => {
    const result = await fetchApi("/ai/generate-graph", {
      method: "POST",
      body: JSON.stringify({ input, interpretation: input }),
    });
    return {
      ...result,
      edges: mapEdgesFromBackend(result.edges),
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
  parseGoal: async (input) => {
    return await fetchApi("/ai/parse-goal", {
      method: "POST",
      body: JSON.stringify({ input }),
    });
  },

  recommendNext: async (planId) => {
    void planId;
    return { recommendedNodeId: null, reason: "后端暂未实现AI推荐" };
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
