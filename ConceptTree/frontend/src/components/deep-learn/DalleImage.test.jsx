import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DalleImage from "./DalleImage.jsx";
import { LanguageProvider } from "../../contexts/LanguageContext.jsx";

describe("DalleImage", () => {
  it("falls back to a localized architecture diagram when image generation is unavailable", () => {
    render(
      <LanguageProvider>
        <DalleImage id="image-1" url="" reason="Gradient checking" />
      </LanguageProvider>,
    );

    expect(screen.getByRole("img", { name: /Gradient checking architecture/i })).toBeInTheDocument();
    expect(screen.getByText("Architecture diagram")).toBeInTheDocument();
    expect(screen.getByText("Concept")).toBeInTheDocument();
    expect(screen.getByText("Mechanism")).toBeInTheDocument();
    expect(screen.getByText("Outcome")).toBeInTheDocument();
  });
});
