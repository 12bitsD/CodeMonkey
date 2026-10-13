export const formatNumber = (value) =>
  new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(
    Number(value || 0),
  );

export const formatPercent = (value) =>
  new Intl.NumberFormat("zh-CN", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(Number(value || 0));

export const formatDateTime = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

export const formatDuration = (value) => {
  const milliseconds = Number(value || 0);
  if (milliseconds < 1000) return `${Math.round(milliseconds)} ms`;
  return `${(milliseconds / 1000).toFixed(2)} s`;
};

export const dateRangeForDays = (days) => {
  const end = new Date();
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - Number(days));
  return { start: start.toISOString(), end: end.toISOString() };
};

export const statusTone = (status) => {
  if (["completed", "ok", "passed"].includes(status)) return "success";
  if (["error", "failed", "abandoned"].includes(status)) return "danger";
  if (["in_progress", "disconnected"].includes(status)) return "warning";
  return "neutral";
};
