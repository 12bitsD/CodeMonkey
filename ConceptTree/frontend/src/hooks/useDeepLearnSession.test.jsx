import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createSessionMock, initializeMock, sendMessageMock, sendCommandMock } = vi.hoisted(() => ({
  createSessionMock: vi.fn(),
  initializeMock: vi.fn(),
  sendMessageMock: vi.fn(),
  sendCommandMock: vi.fn(),
}));

vi.mock("../services/deepLearnApi", () => ({
  deepLearnApi: {
    createSession: createSessionMock,
    initialize: initializeMock,
    sendMessage: sendMessageMock,
    sendCommand: sendCommandMock,
  },
}));

const { useDeepLearnSession } = await import("./useDeepLearnSession.js");

function sseResponse(events) {
  const encoder = new TextEncoder();
  return {
    ok: true,
    body: new ReadableStream({
      start(controller) {
        for (const event of events) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
        }
        controller.close();
      },
    }),
  };
}

function Harness() {
  const {
    isStreaming,
    isInitializing,
    messages,
    conceptsStatus,
    canSendMessage,
    sendMessage,
    sendCommand,
    uiFlags,
  } = useDeepLearnSession({
    planId: "plan-1",
    nodeId: "node-1",
  });
  return (
    <div>
      <span data-testid="streaming">{isStreaming ? "streaming" : "idle"}</span>
      <span data-testid="initializing">{isInitializing ? "initializing" : "ready"}</span>
      <span data-testid="can-send">{canSendMessage ? "yes" : "no"}</span>
      <span data-testid="commands">{uiFlags.showCommands ? "shown" : "hidden"}</span>
      <span data-testid="message">{messages.map((m) => m.content).join("")}</span>
      <span data-testid="kinds">{messages.map((m) => m.kind).join(",")}</span>
      <span data-testid="completed">
        {Object.values(conceptsStatus).filter((status) => ["done", "failed", "skipped"].includes(status)).length}
      </span>
      <button type="button" onClick={() => sendMessage("free text")}>send</button>
      <button type="button" onClick={() => sendCommand("restart")}>restart</button>
    </div>
  );
}

describe("useDeepLearnSession", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createSessionMock.mockResolvedValue({
      data: {
        session_id: "session-1",
        state: "INITIALIZING",
        node_name: "节点",
        node_why: "",
        what_list: ["概念"],
        concepts_status: {},
        weak_points: [],
      },
    });
  });

  it("leaves streaming state when an SSE response closes even without done", async () => {
    initializeMock.mockResolvedValue(
      sseResponse([
        { type: "chunk", text: "第一段" },
        { type: "questions", items: ["问题"] },
      ]),
    );

    render(<Harness />);

    await waitFor(() => {
      expect(screen.getByTestId("message")).toHaveTextContent("第一段");
    });
    await waitFor(() => {
      expect(screen.getByTestId("streaming")).toHaveTextContent("idle");
    });
  });

  it("creates a pending assistant message as soon as the teaching stream starts", async () => {
    initializeMock.mockResolvedValue(
      sseResponse([
        { type: "assistant_start" },
        { type: "done" },
      ]),
    );

    render(<Harness />);

    await waitFor(() => {
      expect(screen.getByTestId("kinds")).toHaveTextContent("text");
    });
    expect(screen.getByTestId("message")).toHaveTextContent("");
  });

  it("does not send free-text messages while waiting for a command", async () => {
    createSessionMock.mockResolvedValue({
      data: {
        session_id: "session-1",
        state: "AWAITING_COMMAND",
        node_name: "node",
        node_why: "",
        what_list: ["concept"],
        concepts_status: { 0: "current" },
        weak_points: [],
        recent_turns: [],
      },
    });

    render(<Harness />);

    await waitFor(() => {
      expect(screen.getByTestId("commands")).toHaveTextContent("shown");
    });
    expect(screen.getByTestId("can-send")).toHaveTextContent("no");

    fireEvent.click(screen.getByRole("button", { name: "send" }));

    expect(sendMessageMock).not.toHaveBeenCalled();
    expect(screen.getByTestId("message")).toHaveTextContent("");
  });

  it("allows free-text messages when resuming a questioning session", async () => {
    createSessionMock.mockResolvedValue({
      data: {
        session_id: "session-1",
        state: "QUESTIONING",
        node_name: "node",
        node_why: "",
        what_list: ["concept"],
        concepts_status: { 0: "current" },
        weak_points: [],
        recent_turns: [],
      },
    });
    sendMessageMock.mockResolvedValue(sseResponse([{ type: "done" }]));

    render(<Harness />);

    await waitFor(() => {
      expect(screen.getByTestId("can-send")).toHaveTextContent("yes");
    });
    expect(screen.getByTestId("commands")).toHaveTextContent("hidden");

    fireEvent.click(screen.getByRole("button", { name: "send" }));

    await waitFor(() => {
      expect(sendMessageMock).toHaveBeenCalledWith("session-1", "free text");
    });
  });

  it("restores persisted question cards when resuming a questioning session", async () => {
    createSessionMock.mockResolvedValue({
      data: {
        session_id: "session-1",
        state: "QUESTIONING",
        node_name: "node",
        node_why: "",
        what_list: ["concept"],
        concepts_status: { 0: "current" },
        weak_points: [],
        recent_turns: [
          { role: "assistant", kind: "text", content: "讲解" },
          { role: "assistant", kind: "questions", content: ["问题一", "问题二"] },
        ],
      },
    });

    render(<Harness />);

    await waitFor(() => {
      expect(screen.getByTestId("kinds")).toHaveTextContent("text,questions");
    });
    expect(screen.getByTestId("message")).toHaveTextContent("讲解问题一,问题二");
  });

  it("adds a fallback question card for old resumed questioning sessions without persisted questions", async () => {
    createSessionMock.mockResolvedValue({
      data: {
        session_id: "session-1",
        state: "QUESTIONING",
        node_name: "node",
        node_why: "",
        what_list: ["缺失值处理"],
        current_concept_index: 0,
        concepts_status: { 0: "current" },
        weak_points: [],
        recent_turns: [
          { role: "assistant", kind: "text", content: "讲解" },
        ],
      },
    });

    render(<Harness />);

    await waitFor(() => {
      expect(screen.getByTestId("kinds")).toHaveTextContent("text,questions");
    });
    expect(screen.getByTestId("message")).toHaveTextContent("缺失值处理");
  });

  it("immediately enters initialization and ignores repeated restart clicks", async () => {
    createSessionMock.mockResolvedValue({
      data: {
        session_id: "session-1",
        state: "AWAITING_COMMAND",
        node_name: "node",
        node_why: "",
        what_list: ["concept"],
        concepts_status: { 0: "done", 1: "done", 2: "done" },
        weak_points: [],
        recent_turns: [
          { role: "assistant", kind: "text", content: "旧讲解" },
        ],
      },
    });
    sendCommandMock.mockResolvedValue(sseResponse([{ type: "restart", new_session_id: "session-2" }]));
    initializeMock.mockResolvedValue(sseResponse([{ type: "assistant_start" }, { type: "done" }]));

    render(<Harness />);

    await waitFor(() => {
      expect(screen.getByTestId("message")).toHaveTextContent("旧讲解");
    });

    expect(screen.getByTestId("completed")).toHaveTextContent("3");

    const restartButton = screen.getByRole("button", { name: "restart" });
    fireEvent.click(restartButton);
    fireEvent.click(restartButton);

    expect(screen.getByTestId("initializing")).toHaveTextContent("initializing");
    expect(screen.getByTestId("message")).toHaveTextContent("");
    expect(screen.getByTestId("completed")).toHaveTextContent("0");

    await waitFor(() => {
      expect(sendCommandMock).toHaveBeenCalledTimes(1);
      expect(initializeMock).toHaveBeenCalledWith("session-2");
    });
  });
});
