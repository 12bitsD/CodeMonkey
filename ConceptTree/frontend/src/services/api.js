/**
 * All HTTP communication with the ConceptTree backend lives here.
 *
 * This module is the single source of truth for API calls. Every request flows
 * through the private `fetchApi` helper, which automatically:
 *   1. Attaches the JWT bearer token from localStorage (if present).
 *   2. Throws a descriptive error when the backend signals failure (`success: false`).
 *   3. Returns only `json.data` — callers never touch the envelope.
 *
 * Field name mismatch — frontend uses `from`/`to` for graph edges; the backend
 * stores them as `from_node`/`to_node`. Use `mapEdgesFromBackend` when reading
 * and `mapEdgesToBackend` when writing to bridge the gap automatically.
 *
 * API groups exported by this module:
 * - `tokenManager`   — read/write/clear the stored JWT.
 * - `authApi`        — register, login, logout.
 * - `userProfileApi` — fetch and update the authenticated user's profile.
 * - `plansApi`       — CRUD for learning plans (create, list, update, archive, delete).
 * - `graphApi`       — AI graph generation and per-node status/position updates.
 * - `notesApi`       — CRUD for per-node notes.
 * - `aiApi`          — AI helpers: goal parsing, goal clarification, next-node recommendation.
 * - `statsApi`       — learning progress statistics.
 *
 * @module services/api
 */
import { createEmptyUserProfile } from "../types";
import { buildApiUrl } from "../config/api";

/** localStorage key under which the JWT is stored. */
const TOKEN_KEY = "concept_tree_token";

/**
 * Thin wrapper around localStorage for reading, writing, and deleting the JWT.
 *
 * Centralising token I/O here means the storage key is defined in exactly one
 * place and is easy to swap (e.g., to sessionStorage or a cookie).
 *
 * @example
 * tokenManager.set(data.token);   // after login
 * const token = tokenManager.get(); // before a request
 * tokenManager.remove();           // on logout
 */
export const tokenManager = {
  /** Returns the stored JWT string, or `null` if not logged in. */
  get: () => localStorage.getItem(TOKEN_KEY),
  /** Persists `token` to localStorage. */
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  /** Clears the stored JWT (called on logout or token parse failure). */
  remove: () => localStorage.removeItem(TOKEN_KEY),
};

/**
 * Core HTTP helper used by every exported API group.
 *
 * Attaches `Content-Type: application/json` and an `Authorization: Bearer`
 * header (when a token exists), calls `fetch`, and unwraps the backend
 * envelope `{ success, data, error }`.
 *
 * Throws if:
 * - The network request itself fails.
 * - `json.success` is `false` — the thrown `Error` carries `json.error.message`.
 *
 * @param {string} endpoint - Path relative to the API base URL, e.g. `/plans`.
 * @param {RequestInit} [options={}] - Standard `fetch` options (method, body, etc.).
 * @returns {Promise<*>} The `data` field from the backend response envelope.
 * @throws {Error} On network failure or when the backend reports an error.
 */
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

/**
 * Converts a backend edge array to frontend format.
 *
 * The backend stores edge endpoints as `from_node` / `to_node`. The frontend
 * uses `from` / `to`. This function renames the fields without losing any
 * other edge properties (e.g., `style`, `label`).
 *
 * Safe to call on already-mapped edges — if `from_node` is absent, `from`
 * is preserved unchanged (prevents double-mapping regression).
 *
 * @param {Array<{from_node?: string, to_node?: string, from?: string, to?: string, [key: string]: *}>} edges
 * @returns {Array<{from: string, to: string, [key: string]: *}>}
 */
export const mapEdgesFromBackend = (edges) =>
  (edges || []).map((e) => {
    const { from_node, to_node, ...rest } = e;
    return {
      ...rest,
      from: from_node || e.from,
      to: to_node || e.to,
    };
  });

/**
 * Converts a frontend edge array to backend format.
 *
 * Inverse of `mapEdgesFromBackend`. Call this before sending edges in any
 * POST / PUT body so the backend receives `from_node` / `to_node`.
 *
 * @param {Array<{from?: string, to?: string, from_node?: string, to_node?: string, [key: string]: *}>} edges
 * @returns {Array<{from_node: string, to_node: string, [key: string]: *}>}
 */
export const mapEdgesToBackend = (edges) =>
  (edges || []).map((e) => {
    const { from, to, ...rest } = e;
    return {
      ...rest,
      from_node: from || e.from_node,
      to_node: to || e.to_node,
    };
  });

// ─── Auth API ─────────────────────────────────────────────────────────────────

/**
 * Authentication endpoints — register, login, and logout.
 *
 * After a successful `login` or `register`, the caller is responsible for
 * storing the returned token via `tokenManager.set(data.token)`. `logout`
 * always clears the token from localStorage even if the backend call fails.
 */
export const authApi = {
  /**
   * Creates a new user account and returns `{ token, user }`.
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{token: string, user: Object}>}
   */
  register: async (email, password) => {
    return await fetchApi("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  /**
   * Authenticates an existing user and returns `{ token, user }`.
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{token: string, user: Object}>}
   */
  login: async (email, password) => {
    return await fetchApi("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  /**
   * Invalidates the session on the backend and removes the local token.
   *
   * The `finally` block guarantees local token cleanup even when the
   * backend call times out or returns an error.
   *
   * @returns {Promise<void>}
   */
  logout: async () => {
    try {
      await fetchApi("/auth/logout", { method: "POST" });
    } finally {
      tokenManager.remove();
    }
  },
};

// ─── User Profile API ─────────────────────────────────────────────────────────

/**
 * Endpoints for the authenticated user's learning profile.
 *
 * The profile (occupation, education level, programming/math levels, etc.) is
 * used to personalise the AI-generated concept graphs. `get` falls back to an
 * empty profile so callers never need to null-check the return value.
 */
export const userProfileApi = {
  /**
   * Fetches the current user's profile.
   *
   * Returns an empty profile (via `createEmptyUserProfile`) when the backend
   * is unreachable, so UI components always receive a valid shape.
   *
   * @returns {Promise<import('../types').UserProfile>}
   */
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

  /**
   * Replaces the user's profile with `profile` and returns the saved version.
   * @param {import('../types').UserProfile} profile
   * @returns {Promise<import('../types').UserProfile>}
   */
  update: async (profile) => {
    return await fetchApi("/user/profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    });
  },
};

// ─── Plans API ────────────────────────────────────────────────────────────────

/**
 * CRUD operations for learning plans.
 *
 * A plan bundles a concept graph (nodes + edges) with metadata (title, progress).
 * `list` never throws — it returns `[]` on backend failure so the UI degrades
 * gracefully. All edge arrays are automatically converted via `mapEdgesToBackend`
 * before sending to avoid field-name mismatches.
 */
export const plansApi = {
  /**
   * Returns all plans for the authenticated user, newest first.
   *
   * Falls back to `[]` when the backend is unavailable.
   *
   * @returns {Promise<import('../types').Plan[]>}
   */
  list: async () => {
    try {
      return await fetchApi("/plans");
    } catch (e) {
      console.warn("Backend unavailable, falling back to empty list", e);
      return [];
    }
  },

  /**
   * Creates a new plan from an AI-generated graph result.
   *
   * @param {Object} params
   * @param {string} params.title - Human-readable plan title.
   * @param {string} params.originalInput - The raw user input that triggered graph generation.
   * @param {string} params.targetNodeId - ID of the root / goal node.
   * @param {import('../types').GraphNode[]} params.nodes
   * @param {import('../types').GraphEdge[]} params.edges - Frontend-format edges; converted automatically.
   * @returns {Promise<import('../types').Plan>} The newly created plan.
   */
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

  /**
   * Partial-updates a plan by ID.
   *
   * If `data` contains an `edges` array it is converted to backend format
   * before sending.
   *
   * @param {string} id - Plan ID.
   * @param {Partial<import('../types').Plan & { nodes: import('../types').GraphNode[], edges: import('../types').GraphEdge[] }>} data
   * @returns {Promise<import('../types').Plan>} The updated plan.
   */
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

  /**
   * Moves a plan to archived status.
   * @param {string} id
   * @returns {Promise<*>}
   */
  archive: async (id) => {
    return await fetchApi(`/plans/${id}/archive`, {
      method: "PUT",
    });
  },

  /**
   * Restores an archived plan to active status.
   * @param {string} id
   * @returns {Promise<*>}
   */
  restore: async (id) => {
    return await fetchApi(`/plans/${id}/restore`, {
      method: "PUT",
    });
  },

  /**
   * Permanently deletes a plan.
   * @param {string} id
   * @returns {Promise<*>}
   */
  delete: async (id) => {
    return await fetchApi(`/plans/${id}`, {
      method: "DELETE",
    });
  },
};

// ─── Graph API ────────────────────────────────────────────────────────────────

/**
 * Graph generation and per-node mutation endpoints.
 *
 * All methods that return graph data call `mapEdgesFromBackend` so the caller
 * always receives `from`/`to` fields, never `from_node`/`to_node`.
 */
export const graphApi = {
  /**
   * Asks the AI to generate a concept dependency graph for a learning goal.
   *
   * Optionally enriches the prompt with the user's background so the AI can
   * skip concepts the user already knows.
   *
   * @param {string} input - The learning goal typed by the user.
   * @param {import('../types').UserProfile|null} [userProfile=null] - If provided, personalises the graph.
   * @returns {Promise<{ nodes: import('../types').GraphNode[], edges: import('../types').GraphEdge[], targetNodeId: string, interpretation: string }>}
   */
  generate: async (input, userProfile = null) => {
    const body = { input, interpretation: input };
    if (userProfile) {
      body.userBackground = {
        occupation: userProfile.occupation || "",
        education: userProfile.education || "",
        programmingLevel: userProfile.programmingLevel || "",
        mathLevel: userProfile.mathLevel || "",
        abilities: userProfile.abilities || [],
        masteredKnowledge: userProfile.masteredKnowledge || [],
      };
    }
    const result = await fetchApi("/ai/generate-graph", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return {
      ...result,
      edges: mapEdgesFromBackend(result.edges),
    };
  },

  /**
   * Fetches the full graph (nodes + edges) for an existing plan.
   * @param {string} planId
   * @returns {Promise<{ nodes: import('../types').GraphNode[], edges: import('../types').GraphEdge[] }>}
   */
  get: async (planId) => {
    const result = await fetchApi(`/plans/${planId}/graph`);
    return {
      ...result,
      edges: mapEdgesFromBackend(result.edges),
    };
  },

  /**
   * Updates a single node's learning status (`unlearned` | `learned` | `skipped`).
   *
   * The backend recalculates plan progress and returns updated progress counters.
   *
   * @param {string} planId
   * @param {string} nodeId
   * @param {'unlearned'|'learned'|'skipped'} status
   * @returns {Promise<{ status: string, plan: { progress: number, total: number } }>}
   */
  updateNodeStatus: async (planId, nodeId, status) => {
    return await fetchApi(`/plans/${planId}/nodes/${nodeId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
  },

  /**
   * Persists the canvas position of a dragged node.
   * @param {string} planId
   * @param {string} nodeId
   * @param {number} x - Canvas X coordinate.
   * @param {number} y - Canvas Y coordinate.
   * @returns {Promise<{ x: number, y: number }>}
   */
  updateNodePosition: async (planId, nodeId, x, y) => {
    return await fetchApi(`/plans/${planId}/nodes/${nodeId}/position`, {
      method: "PUT",
      body: JSON.stringify({ x, y }),
    });
  },

  /**
   * Applies a batch of user-requested graph edits (keep / remove / add nodes)
   * via the AI reconciliation endpoint.
   *
   * @param {string} planId
   * @param {{ keep: string[], remove: string[], add: string[], newTitle?: string }} changes
   * @returns {Promise<*>} The updated graph.
   */
  applyChanges: async (planId, { keep, remove, add, newTitle }) => {
    return await fetchApi(`/plans/${planId}/apply-changes`, {
      method: "POST",
      body: JSON.stringify({ keep, remove, add, newTitle }),
    });
  },
};

// ─── Notes API ────────────────────────────────────────────────────────────────

/**
 * Per-node Markdown notes attached to a plan.
 *
 * Notes let users annotate individual concept nodes while studying. They are
 * scoped by `planId` + `nodeId` and support Markdown content.
 */
export const notesApi = {
  /**
   * Lists notes for a specific plan, or all notes when `planId` is omitted.
   * @param {string|null} [planId=null]
   * @returns {Promise<import('../types').Note[]>}
   */
  list: async (planId = null) => {
    const params = planId ? `?planId=${planId}` : "";
    return await fetchApi(`/notes${params}`);
  },

  /**
   * Creates a new note attached to a specific node in a plan.
   * @param {string} planId
   * @param {string} nodeId
   * @param {string} content - Markdown text.
   * @returns {Promise<import('../types').Note>}
   */
  create: async (planId, nodeId, content) => {
    return await fetchApi("/notes", {
      method: "POST",
      body: JSON.stringify({ planId, nodeId, content }),
    });
  },

  /**
   * Replaces the content of an existing note.
   * @param {string} noteId
   * @param {string} content - New Markdown text.
   * @returns {Promise<import('../types').Note>}
   */
  update: async (noteId, content) => {
    return await fetchApi(`/notes/${noteId}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    });
  },

  /**
   * Permanently deletes a note.
   * @param {string} noteId
   * @returns {Promise<*>}
   */
  delete: async (noteId) => {
    return await fetchApi(`/notes/${noteId}`, {
      method: "DELETE",
    });
  },
};

// ─── AI API ───────────────────────────────────────────────────────────────────

/**
 * AI-powered helper endpoints that call the backend LLM integration.
 *
 * These are separate from `graphApi.generate` because they don't operate on
 * graph structure — they assist with goal interpretation and study planning.
 */
export const aiApi = {
  /**
   * Parses a free-form user goal string into a structured learning intent.
   * @param {string} input - Raw user goal text.
   * @returns {Promise<{ parsedGoal: string, [key: string]: * }>}
   */
  parseGoal: async (input) => {
    return await fetchApi("/ai/parse-goal", {
      method: "POST",
      body: JSON.stringify({ input }),
    });
  },

  /**
   * Regenerates or refines an existing plan's graph based on a revised goal.
   *
   * Optionally associates the clarification with an existing plan ID so the
   * backend can apply changes in-place rather than creating a new plan.
   *
   * @param {string} originalGoal - The goal text when the plan was first created.
   * @param {string} newGoal - The user's updated goal description.
   * @param {string|null} [planId=null] - Existing plan to refine, if any.
   * @returns {Promise<*>}
   */
  clarifyGoal: async (originalGoal, newGoal, planId = null) => {
    return await fetchApi("/ai/clarify-goal", {
      method: "POST",
      body: JSON.stringify({ originalGoal, newGoal, ...(planId ? { planId } : {}) }),
    });
  },

  /**
   * Asks the AI to recommend the next concept node the user should study.
   *
   * The backend considers the user's progress within the plan and the graph
   * dependency order to return a single recommended node with a reason.
   *
   * @param {string} planId
   * @returns {Promise<{ recommended_node_id: string, reason: string }>}
   */
  recommendNext: async (planId) => {
    return await fetchApi("/ai/recommend-next", {
      method: "POST",
      body: JSON.stringify({ planId }),
    });
  },
};

// ─── Stats API ────────────────────────────────────────────────────────────────

/**
 * Learning progress statistics for the authenticated user.
 *
 * Used by the MyLearning dashboard to display progress summaries and
 * knowledge distribution charts.
 */
export const statsApi = {
  /**
   * Returns top-level progress stats (total plans, nodes learned, etc.).
   * @returns {Promise<*>}
   */
  getOverview: async () => {
    return await fetchApi("/stats/overview");
  },

  /**
   * Returns a breakdown of learned nodes grouped by knowledge domain or category.
   * @returns {Promise<*>}
   */
  getDistribution: async () => {
    return await fetchApi("/stats/distribution");
  },
};
