import { createEmptyUserProfile } from "../types";
import { buildApiUrl } from "../config/api";

// Token管理
const TOKEN_KEY = "concept_tree_token";

export const tokenManager = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  remove: () => localStorage.removeItem(TOKEN_KEY),
};

// Helper for fetch
const fetchApi = async (endpoint, options = {}) => {
  try {
    const headers = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    // 自动添加认证token
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

const STORAGE_KEYS = {
  PROFILE: "concept_tree_profile",
  NOTES: "concept_tree_notes",
};

// 本地存储帮助函数 (保留用于 UserProfile 和 Notes)
const storage = {
  get: (key, defaultValue) => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
      console.error(`Error reading ${key} from localStorage`, e);
      return defaultValue;
    }
  },
  set: (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.error(`Error writing ${key} to localStorage`, e);
    }
  },
};

// 模拟延迟
const delay = (ms = 300) => new Promise((resolve) => setTimeout(resolve, ms));

// 认证 API (Real Backend)
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

// 用户画像 API (Real Backend)
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

// 学习计划 API (Hybrid: List/Get from Backend, Create/Update Mocked/Partial)
export const plansApi = {
  list: async () => {
    // 替换为真实后端调用
    try {
      return await fetchApi("/plans");
    } catch (e) {
      console.warn("Backend unavailable, falling back to empty list", e);
      return [];
    }
  },

  create: async (input) => {
    // 暂时保持 Mock，因为后端还没有 /api/plans 的 POST 实现
    // TODO: Implement POST /api/plans in backend
    console.warn("create plan is still mocked client-side");
    return {
      id: `p${Date.now()}`,
      title: input.title || "前端Mock计划",
      progress: 0,
      total: 0,
      status: "active",
      lastAccess: "刚刚",
      createdAt: new Date().toISOString(),
    };
  },

  update: async (id, data) => {
    // Mock
    return { ...data, id };
  },

  archive: async (id) => {
    // Mock
    return { id, status: "archived" };
  },

  restore: async (id) => {
    // Mock
    return { id, status: "active" };
  },

  delete: async (id) => {
    // Mock
    return { id, success: true };
  },
};

// 图谱 API (Real Backend)
export const graphApi = {
  generate: async (input, userProfile) => {
    void userProfile;
    // 后端尚未实现 AI 生成，保持 Mock
    await delay(1500);
    return {
      interpretation: input,
      nodes: [],
      edges: [],
      targetNodeId: "n1",
    };
  },

  get: async (planId) => {
    return await fetchApi(`/plans/${planId}/graph`);
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

// 笔记 API (Mock)
export const notesApi = {
  list: async (planId = null) => {
    await delay();
    const notes = storage.get(STORAGE_KEYS.NOTES, []);
    if (planId) {
      return notes.filter((n) => n.planId === planId);
    }
    return notes;
  },

  create: async (planId, nodeId, content) => {
    await delay();
    const notes = storage.get(STORAGE_KEYS.NOTES, []);
    const newNote = {
      id: `n${Date.now()}`,
      planId,
      nodeId,
      content,
      date: new Date().toLocaleDateString("zh-CN", {
        month: "numeric",
        day: "numeric",
      }),
      createdAt: new Date().toISOString(),
    };

    const updatedNotes = [newNote, ...notes];
    storage.set(STORAGE_KEYS.NOTES, updatedNotes);
    return newNote;
  },

  update: async (noteId, content) => {
    await delay();
    const notes = storage.get(STORAGE_KEYS.NOTES, []);
    const updatedNotes = notes.map((n) =>
      n.id === noteId ? { ...n, content } : n,
    );
    storage.set(STORAGE_KEYS.NOTES, updatedNotes);
    return { id: noteId, content };
  },

  delete: async (noteId) => {
    await delay();
    const notes = storage.get(STORAGE_KEYS.NOTES, []);
    const updatedNotes = notes.filter((n) => n.id !== noteId);
    storage.set(STORAGE_KEYS.NOTES, updatedNotes);
    return { success: true };
  },
};

// AI API (Mock)
export const aiApi = {
  parseGoal: async (input, userProfile) => {
    void userProfile;
    await delay(1000);
    return {
      interpretation: input,
      backgroundSummary: [],
      suggestedNodeCount: 5,
      shouldSplit: false,
      splitSuggestions: null,
    };
  },

  recommendNext: async (planId) => {
    void planId;
    await delay(500);
    return { recommendedNodeId: null, reason: "后端暂未集成AI推荐" };
  },
};
