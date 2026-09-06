import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DeepLearnChat from "./DeepLearnChat.jsx";

const baseProps = {
  canSendMessage: true,
  uiFlags: { showCommands: false, showTestConfirm: null, showFailOptions: null },
  onSendMessage: vi.fn(),
  onSendCommand: vi.fn(),
};

describe("DeepLearnChat", () => {
  it("renders markdown inside question cards", () => {
    const { container } = render(
      <DeepLearnChat
        {...baseProps}
        isStreaming={false}
        messages={[
          {
            id: "q1",
            role: "assistant",
            kind: "questions",
            content: ["**诊断题** 假设你要创建数组，应该使用哪个函数？"],
          },
        ]}
      />,
    );

    expect(screen.getByText("诊断题")).toBeInTheDocument();
    expect(container.querySelector("strong")).toHaveTextContent("诊断题");
  });

  it("uses a full assistant bubble while waiting for a response", () => {
    render(
      <DeepLearnChat
        {...baseProps}
        isStreaming
        messages={[
          { id: "a1", role: "assistant", kind: "text", content: "" },
        ]}
      />,
    );

    expect(screen.getByText("AI 回复")).toBeInTheDocument();
    const bubble = screen.getByText("AI 回复").parentElement;
    expect(bubble?.className).toContain("min-w-[min(440px,100%)]");
  });
  it("shows the comprehensive test confirmation command", () => {
    const onSendCommand = vi.fn();
    render(
      <DeepLearnChat
        {...baseProps}
        isStreaming={false}
        messages={[]}
        uiFlags={{
          showCommands: false,
          showTestConfirm: {
            message: "ready for test?",
            commands: ["confirm_test", "not_ready"],
          },
          showFailOptions: null,
        }}
        onSendCommand={onSendCommand}
      />,
    );

    expect(screen.getByText("ready for test?")).toBeInTheDocument();

    const commandButtons = screen
      .getAllByRole("button")
      .filter((button) => !button.disabled);
    fireEvent.click(commandButtons[0]);

    expect(onSendCommand).toHaveBeenCalledWith("confirm_test");
  });
  it("contains long teaching content without shifting the composer", () => {
    render(
      <DeepLearnChat
        {...baseProps}
        isStreaming={false}
        messages={[{
          id: "long-answer",
          role: "assistant",
          kind: "text",
          content: "error=".repeat(120),
        }]}
      />,
    );

    expect(screen.getByTestId("deep-learn-chat")).toHaveClass("min-w-0", "overflow-hidden");
    expect(screen.getByTestId("deep-learn-scroll-area")).toHaveClass("min-w-0", "overflow-x-hidden");
    expect(screen.getByTestId("deep-learn-composer")).toHaveClass("min-w-0");
  });
});
