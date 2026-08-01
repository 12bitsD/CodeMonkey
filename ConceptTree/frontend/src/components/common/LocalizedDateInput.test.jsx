import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import LocalizedDateInput, { formatLocalizedDate } from "./LocalizedDateInput";

describe("LocalizedDateInput", () => {
  it("uses an English placeholder independent of the operating-system locale", () => {
    render(<LocalizedDateInput language="en" aria-label="Deadline" />);

    expect(screen.getByText("MM / DD / YYYY")).toBeInTheDocument();
  });

  it("formats stored dates according to the selected application language", () => {
    expect(formatLocalizedDate("2026-08-02", "en")).toBe("08 / 02 / 2026");
    expect(formatLocalizedDate("2026-08-02", "zh-CN")).toBe("2026 / 08 / 02");
  });
});
