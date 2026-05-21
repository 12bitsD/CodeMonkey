/**
 * Sprint 3 frontend API tests
 * Tests for aiApi.explainTopic() and aiApi.chatStream() SSE methods.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

// ─── Mocks ───────────────────────────────────────────────────────────────────

const TOKEN = "test-token-sprint3";

vi.stubGlobal("localStorage", {
  getItem: vi.fn((k) => (k === "concept_tree_token" ? TOKEN : null)),
  setItem: vi.fn(),
  removeItem: vi.fn(),
});

// Helper: build a SSE stream from an array of event objects
function buildSseStream(events) {
  const lines = events
    .map((ev) => `data: ${JSON.stringify(ev)}\n\n`)
    .join("");
  const encoder = new TextEncoder();
  const encoded = encoder.encode(lines);

  let pos = 0;
  const readableStream = new ReadableStream({
    pull(controller) {
      if (pos >= encoded.length) {
        controller.close();
        return;
      }
      // Yield in small chunks (50 bytes each) to test buffering
      const chunk = encoded.slice(pos, pos + 50);
      pos += 50;
      controller.enqueue(chunk);
    },
  });

  return readableStream;
}

function mockFetch(events, status = 200) {
  const stream = buildSseStream(events);
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status < 400,
      status,
      body: { getReader: () => stream.getReader() },
    })
  );
}

// ─── Import after mocks ───────────────────────────────────────────────────────

const { aiApi } = await import("./api.js");

// ─── explainTopic Tests ───────────────────────────────────────────────────────

describe("aiApi.explainTopic", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends POST to /api/ai/explain-topic with correct body", async () => {
    mockFetch([
      { type: "chunk", text: "导数是" },
      { type: "chunk", text: "函数的变化率" },
      { type: "done" },
    ]);

    await aiApi.explainTopic(
      "node_123",
      0,
      "导数的定义",
      { nodeName: "导数基础", planTitle: "数学" },
      () => {}
    );

    expect(fetch).toHaveBeenCalledOnce();
    const [url, options] = fetch.mock.calls[0];
    expect(url).toContain("/ai/explain-topic");
    expect(options.method).toBe("POST");
    const body = JSON.parse(options.body);
    expect(body.nodeId).toBe("node_123");
    expect(body.topicIndex).toBe(0);
    expect(body.topicText).toBe("导数的定义");
    expect(body.nodeContext.nodeName).toBe("导数基础");
  });

  it("includes Authorization header from localStorage token", async () => {
    mockFetch([{ type: "chunk", text: "内容" }, { type: "done" }]);

    await aiApi.explainTopic("n1", 0, "topic", { nodeName: "节点" }, () => {});

    const [, options] = fetch.mock.calls[0];
    expect(options.headers["Authorization"]).toBe(`Bearer ${TOKEN}`);
  });

  it("passes AbortController signal to explain-topic fetch", async () => {
    mockFetch([{ type: "chunk", text: "内容" }, { type: "done" }]);
    const controller = new AbortController();

    await aiApi.explainTopic(
      "n1",
      0,
      "topic",
      { nodeName: "节点" },
      () => {},
      { signal: controller.signal },
    );

    const [, options] = fetch.mock.calls[0];
    expect(options.signal).toBe(controller.signal);
  });

  it("calls onChunk for each chunk event", async () => {
    mockFetch([
      { type: "chunk", text: "第一段" },
      { type: "chunk", text: "第二段" },
      { type: "chunk", text: "第三段" },
      { type: "done" },
    ]);

    const chunks = [];
    await aiApi.explainTopic("n1", 0, "topic", { nodeName: "节点" }, (chunk) => {
      chunks.push(chunk);
    });

    expect(chunks).toEqual(["第一段", "第二段", "第三段"]);
  });

  it("returns accumulated full text", async () => {
    mockFetch([
      { type: "chunk", text: "Hello " },
      { type: "chunk", text: "World" },
      { type: "done" },
    ]);

    const result = await aiApi.explainTopic("n1", 0, "topic", { nodeName: "节点" }, () => {});
    expect(result).toBe("Hello World");
  });

  it("ignores done event when computing accumulated text", async () => {
    mockFetch([
      { type: "chunk", text: "only" },
      { type: "done", cached: true },
    ]);

    const result = await aiApi.explainTopic("n1", 0, "topic", { nodeName: "n" }, () => {});
    expect(result).toBe("only");
  });

  it("throws on error event in stream", async () => {
    mockFetch([
      { type: "error", error: { code: "AI_ERROR", message: "LLM failed" } },
    ]);

    await expect(
      aiApi.explainTopic("n1", 0, "topic", { nodeName: "n" }, () => {})
    ).rejects.toThrow("LLM failed");
  });

  it("throws on HTTP error status", async () => {
    mockFetch([], 500);

    await expect(
      aiApi.explainTopic("n1", 0, "topic", { nodeName: "n" }, () => {})
    ).rejects.toThrow();
  });

  it("works when onChunk is null (no callback)", async () => {
    mockFetch([{ type: "chunk", text: "text" }, { type: "done" }]);

    const result = await aiApi.explainTopic("n1", 0, "topic", { nodeName: "n" }, null);
    expect(result).toBe("text");
  });
});

// ─── chatStream Tests ─────────────────────────────────────────────────────────

describe("aiApi.chatStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends POST to /api/ai/chat with messages and nodeContext", async () => {
    mockFetch([
      { type: "chunk", text: "梯度" },
      { type: "chunk", text: "是向量" },
      { type: "done" },
    ]);

    const messages = [
      { role: "user", content: "什么是梯度？" },
      { role: "assistant", content: "梯度是..." },
      { role: "user", content: "能举例说明吗？" },
    ];
    const nodeContext = { nodeName: "梯度下降", planTitle: "机器学习" };

    await aiApi.chatStream(messages, nodeContext, () => {});

    expect(fetch).toHaveBeenCalledOnce();
    const [url, options] = fetch.mock.calls[0];
    expect(url).toContain("/ai/chat");
    expect(options.method).toBe("POST");
    const body = JSON.parse(options.body);
    expect(body.messages).toEqual(messages);
    expect(body.nodeContext).toEqual(nodeContext);
  });

  it("includes Authorization header", async () => {
    mockFetch([{ type: "chunk", text: "ok" }, { type: "done" }]);

    await aiApi.chatStream([{ role: "user", content: "hi" }], null, () => {});

    const [, options] = fetch.mock.calls[0];
    expect(options.headers["Authorization"]).toBe(`Bearer ${TOKEN}`);
  });

  it("passes AbortController signal to chat fetch", async () => {
    mockFetch([{ type: "chunk", text: "ok" }, { type: "done" }]);
    const controller = new AbortController();

    await aiApi.chatStream([{ role: "user", content: "hi" }], null, {
      onChunk: () => {},
      signal: controller.signal,
    });

    const [, options] = fetch.mock.calls[0];
    expect(options.signal).toBe(controller.signal);
  });

  it("calls onChunk for each chunk", async () => {
    mockFetch([
      { type: "chunk", text: "A" },
      { type: "chunk", text: "B" },
      { type: "chunk", text: "C" },
      { type: "done" },
    ]);

    const chunks = [];
    await aiApi.chatStream([{ role: "user", content: "test" }], null, (c) => chunks.push(c));
    expect(chunks).toEqual(["A", "B", "C"]);
  });

  it("returns full accumulated text", async () => {
    mockFetch([
      { type: "chunk", text: "你好" },
      { type: "chunk", text: "，世界" },
      { type: "done" },
    ]);

    const result = await aiApi.chatStream([{ role: "user", content: "hi" }], null, () => {});
    expect(result).toBe("你好，世界");
  });

  it("handles empty chunk list (only done event)", async () => {
    mockFetch([{ type: "done" }]);

    const result = await aiApi.chatStream([{ role: "user", content: "test" }], null, () => {});
    expect(result).toBe("");
  });

  it("throws on error event", async () => {
    mockFetch([{ type: "error", error: { code: "AI_ERROR", message: "Chat failed" } }]);

    await expect(
      aiApi.chatStream([{ role: "user", content: "hi" }], null, () => {})
    ).rejects.toThrow("Chat failed");
  });

  it("works without nodeContext (null)", async () => {
    mockFetch([{ type: "chunk", text: "response" }, { type: "done" }]);

    const result = await aiApi.chatStream([{ role: "user", content: "hi" }], null, () => {});
    expect(result).toBe("response");

    const [, options] = fetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.nodeContext).toBeNull();
  });

  it("sends multi-turn conversation history", async () => {
    mockFetch([{ type: "chunk", text: "answer" }, { type: "done" }]);

    const messages = [
      { role: "user", content: "第一个问题" },
      { role: "assistant", content: "第一个回答" },
      { role: "user", content: "第二个问题" },
    ];
    await aiApi.chatStream(messages, { nodeName: "节点" }, () => {});

    const [, options] = fetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.messages).toHaveLength(3);
    expect(body.messages[2].content).toBe("第二个问题");
  });
});
