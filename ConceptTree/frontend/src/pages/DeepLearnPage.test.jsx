import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DeepLearnPage from "./DeepLearnPage.jsx";

const { deleteNoteMock, navigateMock, useDeepLearnSessionMock, useNoteContextMock } = vi.hoisted(() => ({
  deleteNoteMock: vi.fn(),
  navigateMock: vi.fn(),
  useDeepLearnSessionMock: vi.fn(),
  useNoteContextMock: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
  useParams: () => ({ planId: "plan-1", nodeId: "node-1" }),
}));

vi.mock("../hooks/useDeepLearnSession", () => ({
  useDeepLearnSession: useDeepLearnSessionMock,
}));

vi.mock("../contexts/NoteContext", () => ({
  useNoteContext: useNoteContextMock,
}));

describe("DeepLearnPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    deleteNoteMock.mockResolvedValue();
    useNoteContextMock.mockReturnValue({ allNotes: [], actions: { deleteNote: deleteNoteMock } });
  });

  const mockReadySession = (overrides = {}) => {
    useDeepLearnSessionMock.mockReturnValue({
      session: {
        nodeName: "Pandas数据结构",
        nodeWhy: "",
        whatList: ["Series"],
      },
      messages: [],
      conceptsStatus: {},
      weakPoints: [],
      isStreaming: false,
      isInitializing: false,
      canSendMessage: true,
      uiFlags: { showCommands: false, showTestConfirm: null, showFailOptions: null },
      sendMessage: vi.fn(),
      sendCommand: vi.fn(),
      error: null,
      ...overrides,
    });
  };

  it("keeps a back button visible while the session is loading", () => {
    useDeepLearnSessionMock.mockReturnValue({
      session: null,
      messages: [],
      conceptsStatus: {},
      weakPoints: [],
      isStreaming: false,
      uiFlags: {},
      sendMessage: vi.fn(),
      sendCommand: vi.fn(),
      error: null,
    });

    render(<DeepLearnPage />);

    expect(screen.getByText("正在准备学习环境...")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "返回图谱" }));
    expect(navigateMock).toHaveBeenCalledWith("/graph/plan-1");
  });

  it("shows initialization errors instead of staying on a silent loader", () => {
    useDeepLearnSessionMock.mockReturnValue({
      session: null,
      messages: [],
      conceptsStatus: {},
      weakPoints: [],
      isStreaming: false,
      uiFlags: {},
      sendMessage: vi.fn(),
      sendCommand: vi.fn(),
      error: "createSession failed: 404",
    });

    render(<DeepLearnPage />);

    expect(screen.getByText("createSession failed: 404")).toBeInTheDocument();
    expect(screen.getByText("学习环境准备失败")).toBeInTheDocument();
  });

  it("disables free-text input while the session is waiting for a command", () => {
    const sendMessage = vi.fn();
    useDeepLearnSessionMock.mockReturnValue({
      session: {
        nodeName: "数据清洗",
        whatList: ["缺失值"],
      },
      messages: [],
      conceptsStatus: {},
      weakPoints: [],
      isStreaming: false,
      canSendMessage: false,
      uiFlags: { showCommands: true, showTestConfirm: null, showFailOptions: null },
      sendMessage,
      sendCommand: vi.fn(),
      error: null,
    });

    render(<DeepLearnPage />);

    const input = screen.getByPlaceholderText("请选择下一步操作...");
    expect(input).toBeDisabled();
    expect(screen.getByText("继续 →")).toBeInTheDocument();
    expect(sendMessage).not.toHaveBeenCalled();
  });

  it("shows a trustworthy first-time initialization panel", () => {
    useDeepLearnSessionMock.mockReturnValue({
      session: {
        nodeName: "Pandas数据结构",
        nodeWhy: "",
        whatList: ["Series"],
      },
      messages: [],
      conceptsStatus: {},
      weakPoints: [],
      isStreaming: true,
      isInitializing: true,
      canSendMessage: false,
      uiFlags: { showCommands: false, showTestConfirm: null, showFailOptions: null },
      sendMessage: vi.fn(),
      sendCommand: vi.fn(),
      error: null,
    });

    render(<DeepLearnPage />);

    expect(screen.getByText("正在准备第一次深度学习")).toBeInTheDocument();
    expect(screen.getByText(/只会初始化一次/)).toBeInTheDocument();
    expect(screen.getByLabelText("侧边工作区")).toBeInTheDocument();
  });

  it("renders the right side workspace with the assistant chat", () => {
    mockReadySession();

    render(<DeepLearnPage />);

    const workspace = screen.getByLabelText("侧边工作区");
    expect(screen.getByLabelText("概念列表区域")).toHaveStyle({ width: "288px" });
    expect(screen.getByLabelText("侧边工作区容器")).toHaveStyle({ width: "440px" });
    expect(workspace).toHaveClass("w-full");
    expect(screen.getByRole("button", { name: "侧边聊天" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "浏览器" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("要求后续变更")).toBeInTheDocument();
  });

  it("asks for confirmation before restarting the deep learn session", () => {
    const sendCommand = vi.fn();
    mockReadySession({ sendCommand });

    render(<DeepLearnPage />);

    fireEvent.click(screen.getAllByRole("button")[1]);

    expect(screen.getByText("确认重新开始？")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "取消" }));
    expect(sendCommand).not.toHaveBeenCalled();

    fireEvent.click(screen.getAllByRole("button")[1]);
    fireEvent.click(screen.getByRole("button", { name: "确认重新开始" }));

    expect(sendCommand).toHaveBeenCalledWith("restart");
  });

  it("shows saved node notes below the notes button and opens a rendered side reader", () => {
    mockReadySession();
    useNoteContextMock.mockReturnValue({
      actions: { deleteNote: deleteNoteMock },
      allNotes: [
        {
          id: "note-1",
          planId: "plan-1",
          nodeId: "plan-1_node-1",
          content: "## 侧边笔记\n\n- 已保存内容",
          date: "5/20",
        },
        {
          id: "note-2",
          planId: "plan-1",
          nodeId: "node-2",
          content: "其他节点",
          date: "5/20",
        },
      ],
    });

    render(<DeepLearnPage />);

    fireEvent.click(screen.getAllByRole("button", { name: /侧边笔记/ })[0]);

    expect(screen.getByLabelText("笔记阅读区")).toBeInTheDocument();
    expect(screen.getAllByText("侧边笔记").length).toBeGreaterThan(0);
    expect(screen.getByText("已保存内容")).toBeInTheDocument();
    expect(screen.queryByText("其他节点")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "编辑笔记" }));
    expect(screen.getByText(/当前节点共 1 条笔记/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText("支持 Markdown 语法...")).toHaveValue("## 侧边笔记\n\n- 已保存内容");
  });

  it("deletes a saved node note from the rendered side reader", async () => {
    mockReadySession();
    useNoteContextMock.mockReturnValue({
      actions: { deleteNote: deleteNoteMock },
      allNotes: [
        {
          id: "note-1",
          planId: "plan-1",
          nodeId: "node-1",
          content: "## 待删除笔记\n\n内容",
          date: "5/20",
        },
      ],
    });

    render(<DeepLearnPage />);

    fireEvent.click(screen.getAllByRole("button", { name: /待删除笔记/ })[0]);
    fireEvent.click(screen.getByRole("button", { name: "删除笔记" }));

    expect(deleteNoteMock).toHaveBeenCalledWith("note-1");
  });

  it("opens a browser tab inside the right side workspace", () => {
    mockReadySession();

    render(<DeepLearnPage />);

    fireEvent.click(screen.getByRole("button", { name: "浏览器" }));
    fireEvent.change(screen.getByLabelText("浏览器地址"), {
      target: { value: "localhost:5173" },
    });
    fireEvent.click(screen.getByRole("button", { name: "打开" }));

    expect(screen.getByTitle("侧边浏览器")).toHaveAttribute("src", "http://localhost:5173");
    expect(screen.getByText(/拒绝在侧边栏内嵌显示/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /新窗口/ })).toHaveAttribute("href", "http://localhost:5173");
  });

  it("lets the user resize the three learning panes", () => {
    mockReadySession();
    const rectSpy = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      width: 1280,
      height: 800,
      top: 0,
      left: 0,
      bottom: 800,
      right: 1280,
      x: 0,
      y: 0,
      toJSON: () => {},
    });

    try {
      render(<DeepLearnPage />);

      fireEvent.mouseDown(screen.getByRole("button", { name: "调整概念列表和学习区宽度" }), {
        clientX: 288,
      });
      fireEvent.mouseMove(window, { clientX: 348 });
      fireEvent.mouseUp(window);

      expect(screen.getByLabelText("概念列表区域")).toHaveStyle({ width: "348px" });

      fireEvent.mouseDown(screen.getByRole("button", { name: "调整学习区和侧边工作区宽度" }), {
        clientX: 840,
      });
      fireEvent.mouseMove(window, { clientX: 780 });
      fireEvent.mouseUp(window);

      expect(screen.getByLabelText("侧边工作区容器")).toHaveStyle({ width: "500px" });
    } finally {
      rectSpy.mockRestore();
    }
  });
});
