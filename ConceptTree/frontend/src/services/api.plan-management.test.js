import { afterEach, describe, expect, it, vi } from "vitest";

import { plansApi } from "./api";

describe("plansApi plan management", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("sends archive reason in request body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      text: vi.fn().mockResolvedValue(
        JSON.stringify({
          success: true,
          data: { id: "plan_1", status: "archived", archivedReason: "manual" },
        }),
      ),
      status: 200,
    });

    vi.stubGlobal("fetch", fetchMock);

    await plansApi.archive("plan_1", "manual");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, options] = fetchMock.mock.calls[0];
    expect(options.method).toBe("PUT");
    expect(options.body).toBe(JSON.stringify({ reason: "manual" }));
  });

  it("calls pause and resume endpoints", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      text: vi.fn().mockResolvedValue(
        JSON.stringify({
          success: true,
          data: { id: "plan_1", status: "paused" },
        }),
      ),
      status: 200,
    });

    vi.stubGlobal("fetch", fetchMock);

    await plansApi.pause("plan_1");
    await plansApi.resume("plan_1");

    const calledUrls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(calledUrls.some((url) => url.endsWith("/plans/plan_1/pause"))).toBe(true);
    expect(calledUrls.some((url) => url.endsWith("/plans/plan_1/resume"))).toBe(true);
  });
});
