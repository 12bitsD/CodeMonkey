import { describe, expect, it } from "vitest";
import { getApiErrorMessage, isRecoverableApiError } from "./apiErrorMessages";

describe("apiErrorMessages", () => {
  it("identifies recoverable database errors", () => {
    expect(
      isRecoverableApiError({
        code: "DATABASE_CONNECTION_LOST",
      }),
    ).toBe(true);
  });

  it("maps recoverable database errors to stable user copy", () => {
    expect(
      getApiErrorMessage({
        code: "DATABASE_UNAVAILABLE",
        recoverable: true,
        message: "raw pool error",
      }),
    ).toBe("数据同步暂时不可用，本地内容仍可查看");
  });

  it("keeps non-recoverable messages specific", () => {
    expect(
      getApiErrorMessage({
        code: "BAD_REQUEST",
        recoverable: false,
        message: "截止日期不能早于今天",
      }),
    ).toBe("截止日期不能早于今天");
  });
});
