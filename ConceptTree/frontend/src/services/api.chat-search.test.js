import { afterEach, describe, expect, it, vi } from "vitest";

import { aiApi } from "./api";


function createStreamFromLines(lines) {
  const encoder = new TextEncoder();
  let index = 0;

  return {
    getReader() {
      return {
        read: vi.fn(async () => {
          if (index >= lines.length) {
            return { done: true, value: undefined };
          }
          const value = encoder.encode(lines[index]);
          index += 1;
          return { done: false, value };
        }),
      };
    },
  };
}


describe("aiApi.chatStream web search", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("parses search status, sources and chunks from SSE", async () => {
    const onChunk = vi.fn();
    const onSources = vi.fn();
    const onSearchStatus = vi.fn();

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: createStreamFromLines([
          'data: {"type":"search_status","status":"searching"}\n\n',
          'data: {"type":"chunk","text":"hello"}\n\n',
          'data: {"type":"sources","sources":[{"title":"Official docs","url":"https://example.com/docs","source":"example.com"}]}\n\n',
          'data: {"type":"search_status","status":"done"}\n\n',
          'data: {"type":"done"}\n\n',
        ]),
      }),
    );

    const fullText = await aiApi.chatStream(
      [{ role: "user", content: "latest docs" }],
      { nodeName: "Transformer", planTitle: "Transformer plan" },
      {
        enableWebSearch: true,
        onChunk,
        onSources,
        onSearchStatus,
      },
    );

    expect(fullText).toBe("hello");
    expect(onChunk).toHaveBeenCalledWith("hello");
    expect(onSources).toHaveBeenCalledWith([
      {
        title: "Official docs",
        url: "https://example.com/docs",
        source: "example.com",
      },
    ]);
    expect(onSearchStatus).toHaveBeenNthCalledWith(1, "searching");
    expect(onSearchStatus).toHaveBeenNthCalledWith(2, "done");
  });
});
