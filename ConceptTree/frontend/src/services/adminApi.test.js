import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { adminApi, buildQuery } from "./adminApi";
import { tokenManager } from "./api";

const response = (status, body) => ({
  status,
  text: async () => JSON.stringify(body),
});

describe("adminApi", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", {
      getItem: vi.fn().mockReturnValue("normal-user-token"),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("builds bounded query strings without empty values", () => {
    expect(buildQuery({ limit: 50, cursor: null, status: "completed" })).toBe(
      "?limit=50&status=completed",
    );
  });

  it("keeps the normal login token when the admin session is missing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(401, {
          success: false,
          error: { code: "ADMIN_SESSION_REQUIRED", message: "需要管理员会话" },
        }),
      ),
    );

    await expect(adminApi.me()).rejects.toMatchObject({ status: 401 });

    expect(tokenManager.get()).toBe("normal-user-token");
    expect(localStorage.removeItem).not.toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledWith(
      "/api/admin/me",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("translates frontend session filter names to backend query names", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(200, { success: true, data: { items: [], nextCursor: null } }),
      ),
    );

    await adminApi.sessions({ userId: "user-1", status: "completed" });

    expect(fetch).toHaveBeenCalledWith(
      "/api/admin/sessions?status=completed&user_id=user-1",
      expect.objectContaining({ credentials: "include" }),
    );
  });
});
