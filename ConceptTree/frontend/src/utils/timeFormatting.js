const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

const pluralize = (value, unit) =>
  `${value} ${unit}${value === 1 ? "" : "s"} ago`;

export const formatLastStudied = (value, language, now = new Date()) => {
  if (!value) return null;

  const activityDate = new Date(value);
  const currentDate = now instanceof Date ? now : new Date(now);
  if (
    Number.isNaN(activityDate.getTime()) ||
    Number.isNaN(currentDate.getTime())
  ) {
    return null;
  }

  const elapsed = Math.max(0, currentDate.getTime() - activityDate.getTime());
  const isChinese = language === "zh-CN";

  if (elapsed < MINUTE_MS) return isChinese ? "刚刚" : "Just now";

  if (elapsed < HOUR_MS) {
    const minutes = Math.floor(elapsed / MINUTE_MS);
    return isChinese ? `${minutes} 分钟前` : pluralize(minutes, "minute");
  }

  if (elapsed < DAY_MS) {
    const hours = Math.floor(elapsed / HOUR_MS);
    return isChinese ? `${hours} 小时前` : pluralize(hours, "hour");
  }

  const days = Math.floor(elapsed / DAY_MS);
  if (days === 1) return isChinese ? "昨天" : "Yesterday";
  if (days < 7) return isChinese ? `${days} 天前` : pluralize(days, "day");

  return activityDate.toLocaleDateString(isChinese ? "zh-CN" : "en-US", {
    year: "numeric",
    month: isChinese ? "numeric" : "short",
    day: "numeric",
  });
};
