import { describe, expect, it } from "vitest";

import { buildCompletionHtmlDocument } from "./completionHtml";

describe("buildCompletionHtmlDocument", () => {
  it("builds a standalone HTML document and removes executable markup", () => {
    const document = buildCompletionHtmlDocument({
      title: "学习笔记 <一>",
      contentHtml: `
        <h2>动量法</h2>
        <a href="javascript:alert(1)" onclick="alert(1)">危险链接</a>
        <a href="https://example.com">参考资料</a>
        <script>alert(1)</script>
      `,
      generatedLabel: "生成于 2026/9/21",
      language: "zh-CN",
    });

    expect(document).toContain("<!doctype html>");
    expect(document).toContain("<html lang=\"zh-CN\">");
    expect(document).toContain("学习笔记 &lt;一&gt;");
    expect(document).toContain("<h2>动量法</h2>");
    expect(document).toContain('href="https://example.com"');
    expect(document).not.toContain("javascript:");
    expect(document).not.toContain("onclick");
    expect(document).not.toContain("<script");
  });
});
