import { beforeEach, describe, expect, it, vi } from "vitest";

vi.stubGlobal("localStorage", {
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
});

const { createNoteFromDeepLearn, deepLearnApi } = await import("./deepLearnApi.js");

describe("deepLearnApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.getItem.mockReturnValue(null);
  });

  it("uses the shared /api base exactly once when creating a session", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, data: { session_id: "session-1" } }),
      }),
    );

    await deepLearnApi.createSession({ planId: "plan-1", nodeId: "node-1" });

    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe("/api/deep-learn/sessions");
    expect(url).not.toContain("/api/api/");
    expect(JSON.parse(options.body)).toEqual({ node_id: "node-1", plan_id: "plan-1" });
  });

  it("uses the shared /api base exactly once for SSE endpoints", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));

    await deepLearnApi.initialize("session-1");
    await deepLearnApi.sendMessage("session-1", "hello");
    await deepLearnApi.sendCommand("session-1", "restart");

    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
      "/api/deep-learn/sessions/session-1/initialize",
      "/api/deep-learn/sessions/session-1/message",
      "/api/deep-learn/sessions/session-1/command",
    ]);
  });

  it("creates deep learn notes through the shared notes endpoint", async () => {
    localStorage.getItem.mockReturnValue("token-1");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        text: async () => JSON.stringify({
          success: true,
          data: { id: "note-1", planId: "plan-1", nodeId: "node-1", content: "hello" },
        }),
      }),
    );

    await createNoteFromDeepLearn({ planId: "plan-1", nodeId: "node-1", content: "hello" });

    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe("/api/notes");
    expect(options.method).toBe("POST");
    expect(options.headers.Authorization).toBe("Bearer token-1");
    expect(options.headers["Idempotency-Key"]).toBeTruthy();
    expect(JSON.parse(options.body)).toEqual({
      planId: "plan-1",
      nodeId: "node-1",
      content: "hello",
    });
  });
});
