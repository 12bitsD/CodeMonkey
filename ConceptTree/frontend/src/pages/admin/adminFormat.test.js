import { describe, expect, it } from "vitest";

import { dateRangeForDays, formatDuration, formatPercent, statusTone } from "./adminFormat";

describe("admin formatting", () => {
  it("creates a bounded ISO date range", () => {
    const range = dateRangeForDays(7);
    const duration = new Date(range.end) - new Date(range.start);
    expect(duration).toBe(7 * 24 * 60 * 60 * 1000);
  });

  it("formats product metrics consistently", () => {
    expect(formatPercent(0.625)).toContain("62.5");
    expect(formatDuration(250)).toBe("250 ms");
    expect(formatDuration(1500)).toBe("1.50 s");
    expect(statusTone("error")).toBe("danger");
    expect(statusTone("completed")).toBe("success");
  });
});
