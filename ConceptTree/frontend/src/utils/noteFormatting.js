const MAX_CHAT_BULLETS = 3;
const MAX_LINE_LENGTH = 220;
const MAX_BLOCK_LENGTH = 1200;

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

  const userFocus = userMessages.length
    ? userMessages.map((message) => `- ${trimLine(message.content)}`).join("\n")
    : "- 用户尚未留下明确问题";
  const insights = assistantMessages.length
    ? assistantMessages.map((message) => `- ${trimLine(message.content)}`).join("\n")
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

  return existingNotes.some((note) => normalizeForCompare(note?.content) === normalizedCandidate);
}
