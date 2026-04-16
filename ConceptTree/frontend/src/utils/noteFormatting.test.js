import { describe, expect, it } from "vitest";
import {
  buildChatSummaryNote,
  buildExplainNote,
  hasSimilarNote,
} from "./noteFormatting";

describe("noteFormatting", () => {
  it("builds a structured explain note with node and topic context", () => {
    const result = buildExplainNote("层归一化的工作原理", "这里是 **解释内容**", "层归一化");

    expect(result).toContain("## 核心内容笔记");
    expect(result).toContain("知识点：层归一化");
    expect(result).toContain("主题：层归一化的工作原理");
    expect(result).toContain("这里是 **解释内容**");
  });

  it("builds a compact chat summary note from recent messages", () => {
    const result = buildChatSummaryNote(
      [
        { role: "user", content: "能帮我理解层归一化的作用吗？" },
        { role: "assistant", content: "它能稳定训练过程，并减少内部协变量偏移。" },
        { role: "user", content: "那它和 BatchNorm 的区别呢？" },
      ],
      "层归一化",
    );

    expect(result).toContain("## AI 学习助手总结");
    expect(result).toContain("知识点：层归一化");
    expect(result).toContain("### 用户关注");
    expect(result).toContain("### 关键结论");
  });

  it("detects duplicate notes after whitespace normalization", () => {
    const duplicate = hasSimilarNote(
      [{ content: "## 核心内容笔记\n\n知识点：层归一化\n\n解释内容" }],
      "## 核心内容笔记\r\n\r\n知识点：层归一化\r\n\r\n解释内容",
    );

    expect(duplicate).toBe(true);
  });
});
