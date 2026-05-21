const DB_RECOVERABLE_CODES = new Set([
  "DATABASE_UNAVAILABLE",
  "DATABASE_CONNECTION_LOST",
  "DATABASE_ERROR",
  "SCHEMA_NOT_READY",
  "RATE_LIMITED",
]);

export const isRecoverableApiError = (error) =>
  Boolean(error?.recoverable || DB_RECOVERABLE_CODES.has(error?.code));

export const getApiErrorMessage = (
  error,
  fallback = "操作失败，请稍后重试",
) => {
  if (!error) return fallback;

  if (error.code === "SCHEMA_NOT_READY") {
    return "数据结构正在更新，请稍后刷新";
  }

  if (isRecoverableApiError(error)) {
    return "数据同步暂时不可用，本地内容仍可查看";
  }

  return error.message || fallback;
};
