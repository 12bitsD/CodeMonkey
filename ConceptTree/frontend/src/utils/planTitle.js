const CJK_PATTERN = /[\u3400-\u9fff]/;

export const compactPlanTitle = (value, { maxCjk = 13, maxWords = 7 } = {}) => {
  const title = String(value || "").replace(/\s+/g, " ").trim();
  if (!title) return "";

  if (CJK_PATTERN.test(title)) {
    if (title.length <= maxCjk) return title;
    return `${title.slice(0, maxCjk).replace(/[，、；：,.!?。！？]+$/u, "")}…`;
  }

  const words = title.split(" ");
  if (words.length <= maxWords) return title;
  return `${words.slice(0, maxWords).join(" ").replace(/[,;:.!?]+$/u, "")}…`;
};
