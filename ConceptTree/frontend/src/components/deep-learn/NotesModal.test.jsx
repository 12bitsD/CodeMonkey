import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NotesModal from "./NotesModal.jsx";

const { useNoteContextMock } = vi.hoisted(() => ({
  useNoteContextMock: vi.fn(),
}));

vi.mock("../../contexts/NoteContext", () => ({
  useNoteContext: useNoteContextMock,
}));

describe("NotesModal", () => {
  const addNote = vi.fn();
  const updateNote = vi.fn();
  const deleteNote = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    addNote.mockResolvedValue({ id: "note-new" });
    updateNote.mockResolvedValue({ id: "note-1" });
    deleteNote.mockResolvedValue();
    useNoteContextMock.mockReturnValue({
      allNotes: [
        {
          id: "note-1",
          planId: "plan-1",
          nodeId: "plan-1_node-1",
          content: "## 旧笔记\n\n内容 A",
          date: "5/21",
        },
        {
          id: "note-other",
          planId: "plan-1",
          nodeId: "node-2",
          content: "其他节点笔记",
          date: "5/21",
        },
      ],
      actions: { addNote, deleteNote, updateNote },
    });
  });

  it("shows only notes that belong to the current node and opens them for editing", () => {
    render(
      <NotesModal
        open
        onClose={vi.fn()}
        planId="plan-1"
        nodeId="node-1"
      />,
    );

    expect(screen.getByText("当前节点共 1 条笔记")).toBeInTheDocument();
    expect(screen.getAllByText("旧笔记").length).toBeGreaterThan(0);
    expect(screen.queryByText("其他节点笔记")).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText("支持 Markdown 语法...")).toHaveValue("## 旧笔记\n\n内容 A");
  });

  it("updates an existing node note", async () => {
    render(
      <NotesModal
        open
        onClose={vi.fn()}
        planId="plan-1"
        nodeId="node-1"
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("支持 Markdown 语法..."), {
      target: { value: "## 已编辑" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() => expect(updateNote).toHaveBeenCalledWith("note-1", "## 已编辑"));
    expect(addNote).not.toHaveBeenCalled();
  });

  it("deletes the selected node note from the editor", async () => {
    render(
      <NotesModal
        open
        onClose={vi.fn()}
        planId="plan-1"
        nodeId="node-1"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "删除" }));

    await waitFor(() => expect(deleteNote).toHaveBeenCalledWith("note-1"));
  });

  it("creates a new note from the current node notes panel", async () => {
    render(
      <NotesModal
        open
        onClose={vi.fn()}
        planId="plan-1"
        nodeId="node-1"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "新建笔记" }));
    fireEvent.change(screen.getByPlaceholderText("支持 Markdown 语法..."), {
      target: { value: "# 新笔记" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() => expect(addNote).toHaveBeenCalledWith("plan-1", "node-1", "# 新笔记"));
  });
});
