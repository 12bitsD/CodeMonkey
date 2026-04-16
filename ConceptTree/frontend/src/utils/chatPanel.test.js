import { describe, expect, it } from "vitest";
import {
  clampChatPanelSize,
  getChatPanelLimits,
  getDefaultChatPanelSize,
  getResizedChatPanelSize,
} from "./chatPanel";

describe("chatPanel", () => {
  it("builds viewport-aware limits", () => {
    expect(getChatPanelLimits({ width: 360, height: 640 })).toEqual({
      minWidth: 280,
      maxWidth: 320,
      minHeight: 360,
      maxHeight: 520,
    });
  });

  it("clamps a panel size into the allowed range", () => {
    expect(
      clampChatPanelSize(
        { width: 620, height: 900 },
        { width: 430, height: 640 },
      ),
    ).toEqual({
      width: 390,
      height: 520,
    });
  });

  it("returns a safe default size", () => {
    expect(getDefaultChatPanelSize({ width: 300, height: 500 })).toEqual({
      width: 320,
      height: 420,
    });
  });

  it("grows width and height from the top-right resize handle", () => {
    expect(
      getResizedChatPanelSize(
        { width: 320, height: 420 },
        80,
        -90,
        { width: 1200, height: 900 },
      ),
    ).toEqual({
      width: 400,
      height: 510,
    });
  });
});
