import { describe, expect, it } from "vitest";

import { hasExpandedResources, mergeNodeResources } from "./resourceSearch";

describe("resourceSearch", () => {
  it("merges original and searched resources without duplicates", () => {
    const merged = mergeNodeResources(
      [
        { name: "原始资源", url: "https://example.com/a", reason: "original" },
      ],
      {
        items: [
          { name: "搜索资源", url: "https://example.com/b", reason: "search" },
          { name: "重复资源", url: "https://example.com/a", reason: "dup" },
        ],
      },
    );

    expect(merged).toHaveLength(2);
    expect(merged[0].name).toBe("原始资源");
    expect(merged[1].name).toBe("搜索资源");
  });

  it("detects expanded resources from cache", () => {
    expect(hasExpandedResources({ items: [{ name: "A" }] })).toBe(true);
    expect(hasExpandedResources({ items: [] })).toBe(false);
    expect(hasExpandedResources({})).toBe(false);
  });
});
