import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminPage from "./AdminPage";
import { adminApi } from "../../services/adminApi";

vi.mock("../../services/adminApi", () => ({
  ADMIN_SESSION_EXPIRED_EVENT: "concept-tree-admin-session-expired",
  adminApi: {
    me: vi.fn(),
    elevate: vi.fn(),
    logout: vi.fn(),
    overview: vi.fn(),
    timeseries: vi.fn(),
    users: vi.fn(),
  },
}));

const overview = {
  totalUsers: 12,
  newUsers: 2,
  activeUsers: 8,
  deepSessions: 6,
  completedSessions: 3,
  completionRate: 0.5,
  plansCreated: 4,
  activePlans: 7,
  learningEvents: 21,
  notesCreated: 5,
  totalTokens: 1000,
  traceErrors: 1,
  estimatedCostUsd: 0,
  costTrackingAvailable: false,
};

describe("AdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    adminApi.overview.mockResolvedValue(overview);
    adminApi.timeseries.mockResolvedValue({ items: [] });
    adminApi.users.mockResolvedValue({ items: [], nextCursor: null });
  });

  it("shows password re-entry when the admin cookie is missing", async () => {
    adminApi.me.mockRejectedValue({ status: 401 });
    render(<MemoryRouter initialEntries={["/admin"]}><AdminPage /></MemoryRouter>);

    expect(await screen.findByRole("heading", { name: "管理员验证" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("输入当前登录账户的密码")).toBeInTheDocument();
  });

  it("loads the dashboard only after administrator verification", async () => {
    adminApi.me.mockResolvedValue({ user: { id: "admin-1", role: "admin" } });
    render(<MemoryRouter initialEntries={["/admin/overview"]}><AdminPage /></MemoryRouter>);

    expect(await screen.findByRole("heading", { name: "平台总览" })).toBeInTheDocument();
    await waitFor(() => expect(adminApi.overview).toHaveBeenCalled());
    expect(screen.getByText("费用定价尚未配置")).toBeInTheDocument();
  });

  it("navigates from the icon rail to the users page", async () => {
    adminApi.me.mockResolvedValue({ user: { id: "admin-1", role: "admin" } });
    render(<MemoryRouter initialEntries={["/admin/overview"]}><AdminPage /></MemoryRouter>);

    const userButtons = await screen.findAllByRole("button", { name: "用户" });
    fireEvent.click(userButtons[0]);

    expect(await screen.findByRole("heading", { name: "用户" })).toBeInTheDocument();
    await waitFor(() => expect(adminApi.users).toHaveBeenCalled());
  });
});
