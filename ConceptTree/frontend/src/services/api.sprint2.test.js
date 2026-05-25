/**
 * Sprint 2 Frontend Tests
 * =======================
 * Covers:
 *   F1  – learning_purpose 选项默认值、plansApi.create 传递 learning_purpose
 *   F5  – graphApi.generate 使用 SSE (fetch + ReadableStream)，解析各 event 类型，
 *          调用 onProgress 回调，组装最终数据结构
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// ─── helpers ──────────────────────────────────────────────────────────────────

/** 构造一条 SSE data 行 */
const sseData = (obj) => `data: ${JSON.stringify(obj)}\n\n`;

/**
 * 将若干 SSE 字符串组合成 ReadableStream，模拟 fetch().body
 */
function makeSSEStream(...lines) {
  const encoder = new TextEncoder();
  const chunks = lines.map((l) => encoder.encode(l));
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(chunks[i++]);
      } else {
        controller.close();
      }
    },
  });
}

/**
 * 构造一个完整的 SSE 响应（meta + nodes + edges + done）
 */
function makeFullSSEResponse(nodes = [], edges = []) {
  const meta = sseData({
    type: "meta",
    interpretation: "测试解释",
    targetNodeId: "n1",
    totalNodes: nodes.length,
  });
  const nodeLines = nodes.map((n) => sseData({ type: "node", node: n }));
  const edgesLine = sseData({ type: "edges", edges });
  const doneLine = sseData({ type: "done" });
  return makeSSEStream(meta, ...nodeLines, edgesLine, doneLine);
}

const SAMPLE_NODE = {
  id: "n1",
  name: "核心概念",
  status: "unlearned",
  x: 0,
  y: 0,
  why: "原因",
  what: ["内容"],
  mastery: ["标准"],
  prompt: "提示",
  resources: [],
  isTarget: true,
  phase: "核心",
  phase_order: 2,
  depth_level: 3,
};

// ─── mock setup ───────────────────────────────────────────────────────────────

let fetchMock;

beforeEach(() => {
  // localStorage stub for tokenManager
  vi.stubGlobal("localStorage", {
    getItem: vi.fn(() => "mock-token"),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });

  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ─── graphApi.generate — F5 SSE ───────────────────────────────────────────────

describe("graphApi.generate — F5 SSE client", () => {
  it("使用 fetch 而非 fetchApi（media_type 为 text/event-stream）", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      body: makeFullSSEResponse([SAMPLE_NODE]),
    });

    const { graphApi } = await import("./api.js");
    await graphApi.generate("反向传播", "反向传播");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.method).toBe("POST");
  });

  it("请求 body 中包含 learning_purpose", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      body: makeFullSSEResponse([SAMPLE_NODE]),
    });

    const { graphApi } = await import("./api.js");
    await graphApi.generate("反向传播", "反向传播", null, "master");

    const [, opts] = fetchMock.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.learning_purpose).toBe("master");
  });

  it("默认 learning_purpose 为 apply", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      body: makeFullSSEResponse([SAMPLE_NODE]),
    });

    const { graphApi } = await import("./api.js");
    await graphApi.generate("反向传播", "反向传播");

    const [, opts] = fetchMock.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.learning_purpose).toBe("apply");
  });

  it("Authorization header 包含 token", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      body: makeFullSSEResponse([SAMPLE_NODE]),
    });

    const { graphApi } = await import("./api.js");
    await graphApi.generate("反向传播", "反向传播");

    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.headers["Authorization"]).toBe("Bearer mock-token");
  });

  it("解析 meta 事件并返回 interpretation / targetNodeId", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      body: makeFullSSEResponse([SAMPLE_NODE]),
    });

    const { graphApi } = await import("./api.js");
    const result = await graphApi.generate("反向传播", "反向传播");

    expect(result.interpretation).toBe("测试解释");
    expect(result.targetNodeId).toBe("n1");
  });

  it("解析 node 事件并收集所有节点", async () => {
    const node2 = { ...SAMPLE_NODE, id: "n2", name: "基础知识", isTarget: false };
    fetchMock.mockResolvedValue({
      ok: true,
      body: makeFullSSEResponse([SAMPLE_NODE, node2]),
    });

    const { graphApi } = await import("./api.js");
    const result = await graphApi.generate("反向传播", "反向传播");

    expect(result.nodes).toHaveLength(2);
    expect(result.nodes[0].name).toBe("核心概念");
    expect(result.nodes[1].name).toBe("基础知识");
  });

  it("解析 edges 事件并映射字段（from_node → from）", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      body: makeFullSSEResponse([SAMPLE_NODE], [{ from_node: "n2", to_node: "n1" }]),
    });

    const { graphApi } = await import("./api.js");
    const result = await graphApi.generate("反向传播", "反向传播");

    expect(result.edges).toHaveLength(1);
    expect(result.edges[0].from).toBe("n2");
    expect(result.edges[0].to).toBe("n1");
  });

  it("节点保留 phase / phase_order / depth_level 字段", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      body: makeFullSSEResponse([SAMPLE_NODE]),
    });

    const { graphApi } = await import("./api.js");
    const result = await graphApi.generate("反向传播", "反向传播");

    const node = result.nodes[0];
    expect(node.phase).toBe("核心");
    expect(node.phase_order).toBe(2);
    expect(node.depth_level).toBe(3);
  });

  it("调用 onProgress 回调（meta + node 事件）", async () => {
    const node2 = { ...SAMPLE_NODE, id: "n2", name: "基础知识", isTarget: false };
    fetchMock.mockResolvedValue({
      ok: true,
      body: makeFullSSEResponse([SAMPLE_NODE, node2]),
    });

    const progressEvents = [];
    const { graphApi } = await import("./api.js");
    await graphApi.generate("反向传播", "反向传播", null, "apply", (evt) => {
      progressEvents.push(evt);
    });

    const nodeEvents = progressEvents.filter((e) => e.type === "node");
    expect(nodeEvents).toHaveLength(2);
    expect(nodeEvents[0].received).toBe(1);
    expect(nodeEvents[0].total).toBe(2);
    expect(nodeEvents[1].received).toBe(2);
  });

  it("HTTP 非 200 时抛出错误", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 });

    const { graphApi } = await import("./api.js");
    await expect(graphApi.generate("反向传播", "反向传播")).rejects.toThrow(/HTTP 500/);
  });

  it("SSE error 事件时抛出错误", async () => {
    const errorStream = makeSSEStream(
      sseData({ type: "error", error: { code: "AI_SERVICE_ERROR", message: "模拟 AI 错误" } }),
    );
    fetchMock.mockResolvedValue({ ok: true, body: errorStream });

    const { graphApi } = await import("./api.js");
    await expect(graphApi.generate("反向传播", "反向传播")).rejects.toThrow("模拟 AI 错误");
  });
});

// ─── plansApi.create — F1 learning_purpose ───────────────────────────────────

describe("plansApi.create — F1 learning_purpose", () => {
  beforeEach(() => {
    // plansApi.create 使用 fetchApi（普通 JSON），模拟成功响应
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: { id: "p_test", title: "t" } }),
      text: async () => JSON.stringify({ success: true, data: { id: "p_test", title: "t" } }),
    });
  });

  it("默认 learning_purpose 为 apply", async () => {
    const { plansApi } = await import("./api.js");
    await plansApi.create({
      title: "t",
      originalInput: "i",
      targetNodeId: "n1",
      nodes: [],
      edges: [],
    });

    const [, opts] = fetchMock.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.learning_purpose).toBe("apply");
  });

  it("传入 explore 时发送 explore", async () => {
    const { plansApi } = await import("./api.js");
    await plansApi.create({
      title: "t",
      originalInput: "i",
      targetNodeId: "n1",
      nodes: [],
      edges: [],
      learning_purpose: "explore",
    });

    const [, opts] = fetchMock.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.learning_purpose).toBe("explore");
  });

  it("传入 master 时发送 master", async () => {
    const { plansApi } = await import("./api.js");
    await plansApi.create({
      title: "t",
      originalInput: "i",
      targetNodeId: "n1",
      nodes: [],
      edges: [],
      learning_purpose: "master",
    });

    const [, opts] = fetchMock.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.learning_purpose).toBe("master");
  });

  it("edges 映射为后端格式（from → from_node）", async () => {
    const { plansApi } = await import("./api.js");
    await plansApi.create({
      title: "t",
      originalInput: "i",
      targetNodeId: "n2",
      nodes: [],
      edges: [{ from: "n1", to: "n2" }],
    });

    const [, opts] = fetchMock.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.edges[0].from_node).toBe("n1");
    expect(body.edges[0].to_node).toBe("n2");
  });
});
