import { describe, expect, it, vi } from "vitest";
import {
  persistGeneratedNote,
  saveChatSummaryToNotes,
  saveExplainNoteToNotes,
} from "./noteCapture";

function createDeps() {
  return {
    noteActions: {
      addNote: vi.fn().mockResolvedValue({ id: "note-1" }),
    },
    toast: {
      success: vi.fn(),
      info: vi.fn(),
      error: vi.fn(),
    },
  };
}

describe("noteCapture", () => {
  it("saves explain notes with formatted content", async () => {
    const { noteActions, toast } = createDeps();

    const result = await saveExplainNoteToNotes({
      topicText: "层归一化的工作原理",
      explainContent: "这里是解释内容",
      nodeName: "层归一化",
      existingNotes: [],
      planId: "plan-1",
      selectedNodeId: "node-1",
      noteActions,
      toast,
    });

    expect(result.saved).toBe(true);
    expect(noteActions.addNote).toHaveBeenCalledWith(
      "plan-1",
      "node-1",
      expect.stringContaining("## 核心内容笔记"),
    );
    expect(toast.success).toHaveBeenCalledWith("核心内容已保存到笔记");
  });

  it("saves chat summaries with structured note content", async () => {
    const { noteActions, toast } = createDeps();

    const result = await saveChatSummaryToNotes({
      messages: [
        { role: "user", content: "能帮我总结层归一化的作用吗？" },
        { role: "assistant", content: "它能稳定训练并减少内部协变量偏移。" },
      ],
      nodeName: "层归一化",
      existingNotes: [],
      planId: "plan-1",
      selectedNodeId: "node-1",
      noteActions,
      toast,
    });

    expect(result.saved).toBe(true);
    expect(noteActions.addNote).toHaveBeenCalledWith(
      "plan-1",
      "node-1",
      expect.stringContaining("## AI 学习助手总结"),
    );
    expect(toast.success).toHaveBeenCalledWith("对话总结已保存到笔记");
  });

  it("blocks duplicate note saves before writing", async () => {
    const { noteActions, toast } = createDeps();

    const result = await persistGeneratedNote({
      content: "重复内容",
      existingNotes: [{ content: "重复内容" }],
      planId: "plan-1",
      selectedNodeId: "node-1",
      noteActions,
      toast,
      successMessage: "ok",
      duplicateMessage: "duplicate",
    });

    expect(result.saved).toBe(false);
    expect(result.reason).toBe("duplicate");
    expect(noteActions.addNote).not.toHaveBeenCalled();
    expect(toast.info).toHaveBeenCalledWith("duplicate");
  });

  it("returns a recoverable result when persistence fails", async () => {
    const { noteActions, toast } = createDeps();
    const error = new Error("network down");
    noteActions.addNote.mockRejectedValue(error);

    const result = await persistGeneratedNote({
      content: "需要保存的内容",
      existingNotes: [],
      planId: "plan-1",
      selectedNodeId: "node-1",
      noteActions,
      toast,
      successMessage: "ok",
      duplicateMessage: "duplicate",
    });

    expect(result.saved).toBe(false);
    expect(result.reason).toBe("persist-error");
    expect(result.error).toBe(error);
    expect(toast.success).not.toHaveBeenCalled();
  });

  it("prefers explicit nodeId when saving generated notes", async () => {
    const { noteActions, toast } = createDeps();

    const result = await persistGeneratedNote({
      content: "新的笔记内容",
      existingNotes: [],
      planId: "plan-1",
      nodeId: "node-current",
      selectedNodeId: "node-stale",
      noteActions,
      toast,
      successMessage: "ok",
      duplicateMessage: "duplicate",
    });

    expect(result.saved).toBe(true);
    expect(noteActions.addNote).toHaveBeenCalledWith(
      "plan-1",
      "node-current",
      "新的笔记内容",
    );
  });
});
