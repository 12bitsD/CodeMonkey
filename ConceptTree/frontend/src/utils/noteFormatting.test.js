import { describe, expect, it } from "vitest";
import {
  buildChatSummaryNote,
  buildExplainNote,
  hasSimilarNote,
} from "./noteFormatting";

describe("noteFormatting", () => {
  it("builds a structured explain note with node and topic context", () => {
    const result = buildExplainNote(
      "层归一化的工作原理",
      "这里是 **解释内容**",
      "层归一化",
    );

    expect(result).toContain("## 核心内容笔记");
    expect(result).toContain("知识点：层归一化");
    expect(result).toContain("主题：层归一化的工作原理");
    expect(result).toContain("这里是 **解释内容**");
  });

  it("builds a compact chat summary note from recent messages", () => {
    const result = buildChatSummaryNote(
      [
        { role: "user", content: "能帮我总结一下层归一化和 BatchNorm 的区别吗？" },
        {
          role: "assistant",
          content:
            "层归一化按单个样本的特征维度做归一化，因此不依赖 batch 大小。它在 Transformer 这类序列模型里更稳定。",
        },
      ],
      "层归一化",
    );

    expect(result).toContain("## AI 学习助手总结");
    expect(result).toContain("知识点：层归一化");
    expect(result).toContain("### 用户关注");
    expect(result).toContain("### 关键结论");
    expect(result).toContain("不依赖 batch 大小");
  });

  it("drops long source lists from assistant summaries", () => {
    const result = buildChatSummaryNote(
      [
        { role: "user", content: "帮我找 Transformer 最新论文并总结一下" },
        {
          role: "assistant",
          content: `根据您的要求，我检索到了一些关于 Transformer 的最新论文，这些论文覆盖了不同研究方向和应用场景。

1. CVPR 2021 视觉 Transformer 论文大盘点
- 来源链接: https://example.com/paper
- 摘要: 这是一篇很长很长的列表说明`,
        },
      ],
      "Transformer 架构",
    );

    expect(result).toContain("这些论文覆盖了不同研究方向和应用场景");
    expect(result).not.toContain("来源链接");
    expect(result).not.toContain("CVPR 2021");
  });

  it("detects duplicate notes after whitespace normalization", () => {
    const duplicate = hasSimilarNote(
      [{ content: "## 核心内容笔记\n\n知识点：层归一化\n\n解释内容" }],
      "## 核心内容笔记\r\n\r\n知识点：层归一化\r\n\r\n解释内容",
    );

    expect(duplicate).toBe(true);
  });
});
