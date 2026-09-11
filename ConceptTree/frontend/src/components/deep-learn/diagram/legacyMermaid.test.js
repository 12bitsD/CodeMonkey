import { describe, expect, it } from "vitest";

import {
  convertLegacyMermaid,
  migratePinnedVisuals,
  normalizeLegacyVisualMessage,
} from "./legacyMermaid.js";


describe("legacy Mermaid adapter", () => {
  it("converts the historical LR/TD subset without rendering Mermaid", () => {
    const spec = convertLegacyMermaid("graph LR\nconcept[概念]-->mechanism[机制]\nmechanism-->result[结果]");

    expect(spec.layout).toBe("flow");
    expect(spec.nodes.map((node) => node.title)).toEqual(["概念", "机制", "结果"]);
    expect(spec.edges).toHaveLength(2);
  });

  it("rejects active and unsupported syntax", () => {
    expect(convertLegacyMermaid("sequenceDiagram\nA->>B: hi")).toBeNull();
    expect(convertLegacyMermaid("graph LR\nA-->B\nclick A call dangerous()" )).toBeNull();
  });

  it("migrates legacy pinned strings and removes unconvertible ones", () => {
    const migrated = migratePinnedVisuals([
      { id: "good", url: "mermaid:graph TD\nA[根]-->B[叶]", caption: "旧图" },
      { id: "bad", url: "mermaid:sequenceDiagram\nA->>B: hi", caption: "坏图" },
      { id: "image", url: "/static/image.png", caption: "图片" },
    ]);

    expect(migrated.map((item) => item.id)).toEqual(["good", "image"]);
    expect(migrated[0].kind).toBe("diagram");
    expect(migrated[1].url).toBe("/static/image.png");
  });

  it("normalizes old resumed turns without preserving raw code on failure", () => {
    const message = normalizeLegacyVisualMessage({
      id: "old",
      role: "assistant",
      kind: "mermaid",
      content: "sequenceDiagram\nA->>B: hi",
    });

    expect(message.kind).toBe("legacy_diagram_unavailable");
    expect(JSON.stringify(message)).not.toContain("sequenceDiagram");
  });
});
