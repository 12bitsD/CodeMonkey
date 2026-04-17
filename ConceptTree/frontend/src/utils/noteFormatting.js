const MAX_CHAT_BULLETS = 3;
const MAX_LINE_LENGTH = 220;
const MAX_BLOCK_LENGTH = 1200;
const MAX_SUMMARY_SENTENCE_LENGTH = 120;

function normalizeWhitespace(text) {
  return String(text || "")
    .replace(/\r\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]+/g, " ")
    .trim();
}

function trimLine(text, maxLength = MAX_LINE_LENGTH) {
  const normalized = normalizeWhitespace(text);
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength).trim()}...`;
}

function trimBlock(text, maxLength = MAX_BLOCK_LENGTH) {
  const normalized = normalizeWhitespace(text);
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength).trim()}\n\n...`;
}

function normalizeForCompare(text) {
  return normalizeWhitespace(text)
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, "");
}

function stripMarkdown(text) {
  return normalizeWhitespace(text)
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, "$1")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+\.\s+/gm, "")
    .replace(/^\s*>\s?/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1");
}

function looksLikeSourceLine(text) {
  return /^(来源|参考来源|参考资料|链接|http|www\.)/i.test(text);
}

function looksLikeListHeading(text) {
  return /^(以下|下面|代表性|推荐|论文|资源)/.test(text);
}

function extractAssistantInsights(messages) {
  const candidates = [];

  for (const message of messages) {
    const paragraphs = String(message.content || "")
      .split(/\n+/)
      .map((part) => part.trim())
      .filter(
        (part) =>
          part &&
          !/^\d+\./.test(part) &&
          !/^(来源|来源链接|参考来源|参考资料|链接|摘要)\s*[:：]/i.test(part) &&
          !/^[-*+]\s*(来源|来源链接|参考来源|参考资料|链接|摘要)\s*[:：]/i.test(part),
      )
      .map((part) => stripMarkdown(part));

    for (const paragraph of paragraphs) {
      if (looksLikeSourceLine(paragraph)) continue;
      if (/^https?:\/\//i.test(paragraph)) continue;

      const sentences = paragraph
        .split(/(?<=[。！？!?])\s+|\n+/)
        .map((part) => trimLine(part, MAX_SUMMARY_SENTENCE_LENGTH))
        .filter(
          (part) =>
            part &&
            part.length >= 8 &&
            !looksLikeSourceLine(part) &&
            !looksLikeListHeading(part),
        );

      candidates.push(...sentences);
      if (candidates.length >= MAX_CHAT_BULLETS * 3) break;
    }

    if (candidates.length >= MAX_CHAT_BULLETS * 3) break;
  }

  return Array.from(new Set(candidates)).slice(0, MAX_CHAT_BULLETS);
}

export function buildExplainNote(topicTitle, content, nodeName) {
  const safeTopicTitle = trimLine(topicTitle || "未命名主题");
  const safeNodeName = trimLine(nodeName || "未命名知识点");
  const safeContent = trimBlock(content);

  if (!safeContent) return "";

  return normalizeWhitespace(`## 核心内容笔记

知识点：${safeNodeName}
主题：${safeTopicTitle}

${safeContent}`);
}

export function buildChatSummaryNote(messages, nodeName) {
  const normalizedMessages = Array.isArray(messages)
    ? messages
        .map((message) => ({
          role: message?.role,
          content: normalizeWhitespace(message?.content),
        }))
        .filter((message) => message.content)
    : [];

  if (!normalizedMessages.length) return "";

  const userMessages = normalizedMessages
    .filter((message) => message.role === "user")
    .slice(-MAX_CHAT_BULLETS);
  const assistantMessages = normalizedMessages
    .filter((message) => message.role === "assistant")
    .slice(-MAX_CHAT_BULLETS);
  const assistantInsights = extractAssistantInsights(assistantMessages);

  const userFocus = userMessages.length
    ? userMessages.map((message) => `- ${trimLine(stripMarkdown(message.content))}`).join("\n")
    : "- 用户暂未留下明确问题";
  const insights = assistantInsights.length
    ? assistantInsights.map((message) => `- ${message}`).join("\n")
    : "- 暂无 AI 结论";

  return normalizeWhitespace(`## AI 学习助手总结

知识点：${trimLine(nodeName || "未命名知识点")}

### 用户关注
${userFocus}

### 关键结论
${insights}`);
}

export function hasSimilarNote(existingNotes, candidateContent) {
  const normalizedCandidate = normalizeForCompare(candidateContent);
  if (!normalizedCandidate) return false;

  return existingNotes.some(
    (note) => normalizeForCompare(note?.content) === normalizedCandidate,
  );
}
