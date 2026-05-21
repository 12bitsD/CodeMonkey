import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DeepLearnAssistant from "./DeepLearnAssistant.jsx";

const { chatStreamMock } = vi.hoisted(() => ({
  chatStreamMock: vi.fn(),
}));

vi.mock("../../services/api", () => ({
  aiApi: {
    chatStream: chatStreamMock,
  },
}));

function createFile(name, content, type = "text/markdown") {
  const file = new File([content], name, { type });
  Object.defineProperty(file, "text", {
    value: vi.fn().mockResolvedValue(content),
  });
  return file;
}

describe("DeepLearnAssistant file attachments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    chatStreamMock.mockImplementation(async (_messages, _context, onChunk) => {
      onChunk("ok");
      return "ok";
    });
  });

  it("accepts Markdown files and sends their content as chat context", async () => {
    const { container } = render(
      <DeepLearnAssistant nodeName="AI Native" nodeWhy="practice" />,
    );
    const fileInput = container.querySelector('input[type="file"]');

    fireEvent.change(fileInput, {
      target: { files: [createFile("plan.md", "# Plan\n\nLearn deeply.")] },
    });

    expect(await screen.findByText("plan.md")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("要求后续变更"), {
      target: { value: "总结重点" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    await waitFor(() => expect(chatStreamMock).toHaveBeenCalled());
    const [messages] = chatStreamMock.mock.calls[0];
    expect(messages.at(-1).content).toContain("plan.md");
    expect(messages.at(-1).content).toContain("# Plan");
    expect(messages.at(-1).content).toContain("总结重点");
  });

  it("rejects non-Markdown files with a PDF-forward message", async () => {
    const { container } = render(
      <DeepLearnAssistant nodeName="AI Native" nodeWhy="practice" />,
    );
    const fileInput = container.querySelector('input[type="file"]');

    fireEvent.change(fileInput, {
      target: { files: [createFile("paper.pdf", "%PDF", "application/pdf")] },
    });

    expect(await screen.findByText("目前只支持添加 .md 文件，PDF 会在后续版本支持。")).toBeInTheDocument();
    expect(chatStreamMock).not.toHaveBeenCalled();
  });
});
