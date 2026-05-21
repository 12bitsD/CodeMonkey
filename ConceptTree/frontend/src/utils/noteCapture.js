import {
  buildChatSummaryNote,
  buildExplainNote,
  hasSimilarNote,
} from "./noteFormatting";

export async function persistGeneratedNote({
  content,
  existingNotes,
  planId,
  nodeId,
  selectedNodeId,
  noteActions,
  toast,
  successMessage,
  duplicateMessage,
}) {
  const targetNodeId = nodeId || selectedNodeId;

  if (!targetNodeId || !planId) {
    toast.error("请先选择一个知识点");
    return { saved: false, reason: "missing-context" };
  }

  if (!String(content || "").trim()) {
    toast.info("暂无可保存内容");
    return { saved: false, reason: "empty-content" };
  }

  if (hasSimilarNote(existingNotes, content)) {
    toast.info(duplicateMessage);
    return { saved: false, reason: "duplicate" };
  }

  try {
    await noteActions.addNote(planId, targetNodeId, content);
    toast.success(successMessage);
    return { saved: true, reason: "saved" };
  } catch (error) {
    return { saved: false, reason: "persist-error", error };
  }
}

export async function saveExplainNoteToNotes({
  topicText,
  explainContent,
  nodeName,
  existingNotes,
  planId,
  nodeId,
  selectedNodeId,
  noteActions,
  toast,
}) {
  return persistGeneratedNote({
    content: buildExplainNote(topicText, explainContent, nodeName),
    existingNotes,
    planId,
    nodeId,
    selectedNodeId,
    noteActions,
    toast,
    successMessage: "核心内容已保存到笔记",
    duplicateMessage: "这条核心内容笔记已经保存过了",
  });
}

export async function saveChatSummaryToNotes({
  messages,
  nodeName,
  existingNotes,
  planId,
  nodeId,
  selectedNodeId,
  noteActions,
  toast,
}) {
  return persistGeneratedNote({
    content: buildChatSummaryNote(messages, nodeName),
    existingNotes,
    planId,
    nodeId,
    selectedNodeId,
    noteActions,
    toast,
    successMessage: "对话总结已保存到笔记",
    duplicateMessage: "这段对话总结已经保存过了",
  });
}
