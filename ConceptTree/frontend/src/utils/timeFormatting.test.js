import { describe, expect, it } from "vitest";

import { formatLastStudied } from "./timeFormatting";

const NOW = new Date("2026-08-02T12:00:00.000Z");

describe("formatLastStudied", () => {
  it("turns recent ISO timestamps into concise English relative time", () => {
    expect(formatLastStudied("2026-08-02T11:48:00.000Z", "en", NOW)).toBe(
      "12 minutes ago",
    );
  });

  it("localizes relative time for Chinese", () => {
    expect(formatLastStudied("2026-08-02T07:00:00.000Z", "zh-CN", NOW)).toBe(
      "5 小时前",
    );
  });

  it("uses a compact local date for older activity", () => {
    expect(formatLastStudied("2026-07-01T09:30:00.000Z", "en", NOW)).toBe(
      "Jul 1, 2026",
    );
  });
});
