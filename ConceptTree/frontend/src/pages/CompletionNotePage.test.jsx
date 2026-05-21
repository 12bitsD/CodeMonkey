import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CompletionNotePage from "./CompletionNotePage.jsx";

const { navigateMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
  useParams: () => ({ planId: "plan-1", nodeId: "node-1", noteId: "note-1" }),
}));

describe("CompletionNotePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    Object.defineProperty(window, "print", {
      value: vi.fn(),
      writable: true,
    });
  });

  it("loads the completion note and exports through the browser print dialog", async () => {
    localStorage.setItem("concept_tree_token", "token-1");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "note-1",
        node_id: "node-1",
        session_id: "session-1",
        content: "# 完成笔记\n\n| 概念 | 结论 |\n| --- | --- |\n| 动量法 | 平滑梯度 |",
        created_at: "2026-05-21T00:00:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<CompletionNotePage />);

    expect(await screen.findByRole("heading", { name: "完成笔记" })).toBeInTheDocument();
    expect(screen.getByText("动量法")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/deep-learn/notes/note-1", {
      headers: { Authorization: "Bearer token-1" },
    });

    fireEvent.click(screen.getByRole("button", { name: /导出 PDF/ }));

    expect(window.print).toHaveBeenCalledTimes(1);
  });

  it("keeps the toolbar out of printed output and can return to the learning page", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "note-1",
        content: "## 小结",
        created_at: "2026-05-21T00:00:00Z",
      }),
    }));

    const { container } = render(<CompletionNotePage />);

    await screen.findByRole("heading", { name: "小结" });
    expect(container.querySelector(".print\\:hidden")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "返回" }));

    expect(navigateMock).toHaveBeenCalledWith("/deep-learn/plan-1/node-1");
  });
});
