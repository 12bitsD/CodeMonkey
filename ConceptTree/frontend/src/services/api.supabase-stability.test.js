import { beforeEach, describe, expect, it, vi } from "vitest";

vi.stubGlobal("localStorage", {
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
});

const { ApiError, buildIdempotencyKey, graphApi, notesApi, plansApi } = await import("./api.js");

describe("API recoverable error contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("throws ApiError with backend code and recoverable flag", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 503,
        text: async () =>
          JSON.stringify({
            success: false,
            error: {
              code: "DATABASE_UNAVAILABLE",
              message: "database is temporarily unavailable",
            },
          }),
      }),
    );

    await expect(plansApi.list()).rejects.toMatchObject({
      name: "ApiError",
      code: "DATABASE_UNAVAILABLE",
      status: 503,
      endpoint: "/plans",
      recoverable: true,
    });
  });

  it("does not convert failed plan listing into an empty list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("network down")),
    );

    await expect(plansApi.list()).rejects.toBeInstanceOf(ApiError);
  });

  it("marks bad request data errors as non-recoverable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 400,
        text: async () =>
          JSON.stringify({
            success: false,
            error: {
              code: "DATABASE_INVALID_DATA",
              message: "invalid date",
            },
          }),
      }),
    );

    await expect(plansApi.update("plan-1", { targetEndDate: "bad" })).rejects.toMatchObject({
      code: "DATABASE_INVALID_DATA",
      recoverable: false,
    });
  });

  it("generates stable idempotency keys", () => {
    expect(buildIdempotencyKey("note", "plan-1", "node-1", "content")).toBe(
      buildIdempotencyKey("note", "plan-1", "node-1", "content"),
    );
  });

  it("sends idempotency key for note creation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        text: async () => JSON.stringify({ success: true, data: { id: "note_1" } }),
      }),
    );

    await notesApi.create("plan-1", "node-1", "content", { idempotencyKey: "note-key" });

    const [, options] = fetch.mock.calls[0];
    expect(options.headers["Idempotency-Key"]).toBe("note-key");
  });

  it("sends idempotency key for node status updates", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        text: async () =>
          JSON.stringify({
            success: true,
            data: { nodeId: "node-1", status: "learned", plan: { progress: 1, total: 2 } },
          }),
      }),
    );

    await graphApi.updateNodeStatus("plan-1", "node-1", "learned", {
      idempotencyKey: "status-key",
    });

    const [, options] = fetch.mock.calls[0];
    expect(options.headers["Idempotency-Key"]).toBe("status-key");
  });

  it("uses bulk endpoint for node positions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        text: async () => JSON.stringify({ success: true, data: { updated: 2 } }),
      }),
    );

    await graphApi.updateNodePositions("plan-1", [
      { nodeId: "node-1", x: 1, y: 2 },
      { nodeId: "node-2", x: 3, y: 4 },
    ]);

    const [url, options] = fetch.mock.calls[0];
    expect(url).toContain("/plans/plan-1/nodes/positions");
    expect(JSON.parse(options.body).positions).toHaveLength(2);
  });
});
