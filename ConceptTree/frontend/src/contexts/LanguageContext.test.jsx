import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import {
  LanguageProvider,
  STORAGE_KEY,
  useLanguage,
} from "./LanguageContext";

const LanguageProbe = () => {
  const { language, toggleLanguage, t } = useLanguage();
  return (
    <div>
      <span>{language}</span>
      <span>{t("nav.myLearning")}</span>
      <button type="button" onClick={toggleLanguage}>toggle</button>
    </div>
  );
};

describe("LanguageProvider", () => {
  afterEach(() => {
    window.localStorage.clear();
    document.documentElement.lang = "";
  });

  it("uses English by default and persists a Chinese selection", () => {
    render(
      <LanguageProvider>
        <LanguageProbe />
      </LanguageProvider>,
    );

    expect(screen.getByText("en")).toBeInTheDocument();
    expect(screen.getByText("My Learning")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");

    fireEvent.click(screen.getByRole("button", { name: "toggle" }));

    expect(screen.getByText("zh-CN")).toBeInTheDocument();
    expect(screen.getByText("我的学习")).toBeInTheDocument();
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("zh-CN");
    expect(document.documentElement.lang).toBe("zh-CN");
  });

  it("restores a previously selected language", () => {
    window.localStorage.setItem(STORAGE_KEY, "zh-CN");

    render(
      <LanguageProvider>
        <LanguageProbe />
      </LanguageProvider>,
    );

    expect(screen.getByText("zh-CN")).toBeInTheDocument();
    expect(screen.getByText("我的学习")).toBeInTheDocument();
  });
});
