import { describe, expect, it } from "vitest";
import { createAiRequestRegistry } from "./aiRequestRegistry";

describe("aiRequestRegistry", () => {
  it("aborts the previous request when a key starts again", () => {
    const registry = createAiRequestRegistry();
    const first = registry.begin("chat:p1:n1");
    const second = registry.begin("chat:p1:n1");

    expect(first.signal.aborted).toBe(true);
    expect(second.signal.aborted).toBe(false);
    expect(registry.isCurrent("chat:p1:n1", first.requestId)).toBe(false);
    expect(registry.isCurrent("chat:p1:n1", second.requestId)).toBe(true);
  });

  it("dedupes an active request when requested", () => {
    const registry = createAiRequestRegistry();
    const first = registry.begin("explain:p1:n1:0", { dedupe: true });
    const second = registry.begin("explain:p1:n1:0", { dedupe: true });

    expect(second.deduped).toBe(true);
    expect(second.requestId).toBe(first.requestId);
    expect(first.signal.aborted).toBe(false);
  });

  it("aborts matching requests only", () => {
    const registry = createAiRequestRegistry();
    const chat = registry.begin("chat:p1:n1");
    const explain = registry.begin("explain:p1:n1:0");
    const other = registry.begin("recommend:p1");

    registry.abortMatching((key) => key.startsWith("chat:") || key.startsWith("explain:"));

    expect(chat.signal.aborted).toBe(true);
    expect(explain.signal.aborted).toBe(true);
    expect(other.signal.aborted).toBe(false);
    expect(registry.size()).toBe(1);
  });
});
