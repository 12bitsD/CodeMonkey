import React, { useState, useRef, useEffect, useMemo } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  Share2,
  Edit3,
  CalendarDays,
  Bell,
  Pause,
  Play,
  Plus,
  Minus,
  RotateCcw,
  Check,
  CheckCircle2,
  Circle,
  X,
  Target,
  BookOpen,
  Sparkles,
  FileText,
  Copy,
  ChevronRight,
  Save,
  MessageCircle,
  Send,
  ChevronDown,
  Loader,
  SlidersHorizontal,
} from "lucide-react";
import { Button, Modal } from "../components/ui";
import { InfoSection } from "../components/common";
import ChatMarkdownMessage from "../components/chat/ChatMarkdownMessage";
import MarkdownContent from "../components/common/MarkdownContent";
import { MasteryChecklist } from "../components/node/MasteryChecklist";
import MasteryQuizModal from "../components/node/MasteryQuizModal";
import { ResourceList } from "../components/node/ResourceList";
import { useGraphInteraction } from "../hooks/useGraphInteraction";
import { useGraphContext } from "../contexts/GraphContext";
import { useNoteContext } from "../contexts/NoteContext";
import { usePlanContext } from "../contexts/PlanContext";
import { useToast } from "../contexts/ToastContext";
import { graphApi, aiApi } from "../services/api";
import { toggleNodeStatus, isAllComplete } from "../utils/graphUtils";
import {
  clampChatPanelSize,
  getDefaultChatPanelSize,
  getResizedChatPanelSize,
} from "../utils/chatPanel";
import {
  saveChatSummaryToNotes,
  saveExplainNoteToNotes,
} from "../utils/noteCapture";
import {
  hasExpandedResources,
  mergeNodeResources,
} from "../utils/resourceSearch";
import { createAiRequestRegistry } from "../utils/aiRequestRegistry";
import { calculateLayout } from "../utils/layoutEngine";
import {
  buildMasteryCheckKey,
  generateMasteryQuiz,
} from "../utils/masteryQuiz";

const PLAN_FREQUENCY_OPTIONS = [
  { value: "flexible", label: "灵活安排" },
  { value: "daily", label: "每天学习" },
  { value: "weekly", label: "每周学习" },
  { value: "custom", label: "自定义频率" },
];

const createPlanSettingsState = (plan) => ({
  startDate: plan?.startDate ? String(plan.startDate).slice(0, 10) : "",
  targetEndDate: plan?.targetEndDate ? String(plan.targetEndDate).slice(0, 10) : "",
  studyFrequency: plan?.studyFrequency || "flexible",
  studyDaysPerWeek: plan?.studyDaysPerWeek || 3,
  reminderEnabled: Boolean(plan?.reminderEnabled),
  reminderTime: plan?.reminderTime || "20:00",
  reminderTimezone:
    plan?.reminderTimezone ||
    Intl.DateTimeFormat().resolvedOptions().timeZone ||
    "Asia/Shanghai",
});

const getPlanFrequencyLabel = (frequency, daysPerWeek) => {
  switch (frequency) {
    case "daily":
      return "每天学习";
    case "weekly":
      return "每周复盘";
    case "custom":
      return `每周 ${daysPerWeek || 3} 次`;
    default:
      return "灵活安排";
  }
};

const formatPlanDateLabel = (value) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
};

const getLocalDateInputValue = (value = new Date()) => {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const buildCurvedEdgePath = (from, to, edgeIndex) => {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const distance = Math.hypot(dx, dy);
  if (distance === 0) {
    return `M ${from.x} ${from.y} L ${to.x} ${to.y}`;
  }

  const midX = (from.x + to.x) / 2;
  const midY = (from.y + to.y) / 2;
  const normalX = -dy / distance;
  const normalY = dx / distance;
  const bend = Math.min(Math.max(distance * 0.08, 10), 30);
  const direction = edgeIndex % 2 === 0 ? 1 : -1;
  const controlX = midX + normalX * bend * direction;
  const controlY = midY + normalY * bend * direction;

  return `M ${from.x} ${from.y} Q ${controlX} ${controlY} ${to.x} ${to.y}`;
};

const GraphPage = () => {
  const { planId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const containerRef = useRef(null);
  const draggingPosRef = useRef({ id: null, x: 0, y: 0 });
  const pendingNodePositionsRef = useRef(new Map());
  const positionSaveTimerRef = useRef(null);
  const hasCenteredRef = useRef(false);
  const viewportRef = useRef({ position: { x: 0, y: 0 }, scale: 1 });
  const { plans, actions } = usePlanContext();
  const { allNotes, actions: noteActions } = useNoteContext();
  const { graphsByPlanId, actions: graphActions } = useGraphContext();
  const toast = useToast();

  const plan = plans.find((p) => p.id === planId);
  const cachedGraph = planId ? graphsByPlanId[planId] : null;
  const cachedGraphRef = useRef(cachedGraph);
  const masteryProgressStorageKey = planId
    ? `concept_tree_mastery_progress:${planId}`
    : null;
  const [planTitle, setPlanTitle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isDirty, setIsDirty] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const [showPlanSettings, setShowPlanSettings] = useState(false);
  const [isUpdatingPlanSettings, setIsUpdatingPlanSettings] = useState(false);
  const [planSettings, setPlanSettings] = useState(createPlanSettingsState(plan));
  const [isTogglingPlanStatus, setIsTogglingPlanStatus] = useState(false);
  const [isSharingPlan, setIsSharingPlan] = useState(false);
  const [aiRecommendation, setAiRecommendation] = useState(null);
  const [ghostNodeIds, setGhostNodeIds] = useState(new Set());
  const [masteryProgress, setMasteryProgress] = useState({});
  const [masteryQuiz, setMasteryQuiz] = useState(null);

  useEffect(() => {
    setPlanSettings(createPlanSettingsState(plan));
  }, [plan]);

  useEffect(
    () => () => {
      if (positionSaveTimerRef.current) {
        clearTimeout(positionSaveTimerRef.current);
      }
    },
    [],
  );

  const {
    nodes,
    edges,
    selectedNodeId,
    selectedNode,
    recommendedNode,
    scale,
    position,
    draggingNodeId,
    setSelectedNodeId,
    setDraggingNodeId,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    setNodeStatus,
    setNodes,
    setEdges,
    setPosition,
    resetView,
    zoomIn,
    zoomOut,
  } = useGraphInteraction([], [], aiRecommendation);

  useEffect(() => {
    viewportRef.current = { position, scale };
  }, [position, scale]);

  useEffect(() => {
    cachedGraphRef.current = cachedGraph;
  }, [cachedGraph]);

  useEffect(() => {
    if (!cachedGraph) return;
    if (cachedGraph.title) setPlanTitle(cachedGraph.title);
    setNodes(cachedGraph.nodes || []);
    setEdges(cachedGraph.edges || []);
    setLoading(false);
  }, [cachedGraph, setEdges, setNodes]);

  useEffect(() => {
    hasCenteredRef.current = false;

    const loadGraph = async () => {
      if (!planId) return;
      const graphSnapshot = cachedGraphRef.current;
      setLoading(!graphSnapshot);
      try {
        const data = await graphApi.get(planId);
        if (data && data.nodes) {
          if (data.title) setPlanTitle(data.title);
          setNodes(data.nodes);
          setEdges(data.edges || []);
          graphActions.setGraph(planId, {
            title: data.title || null,
            nodes: data.nodes,
            edges: data.edges || [],
          });
        }
      } catch (err) {
        console.error("Failed to load graph", err);
        if (graphSnapshot?.nodes?.length) {
          toast.error("图谱加载失败，已显示本地缓存");
        } else {
          toast.error("图谱加载失败，请稍后重试");
        }
      } finally {
        setLoading(false);
      }
    };

    loadGraph();
  }, [graphActions, planId, setEdges, setNodes, toast]);

  // Auto-center the canvas once nodes and the container are ready.
  useEffect(() => {
    if (hasCenteredRef.current) return;
    if (nodes.length === 0) return;
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;
    const xs = nodes.map((n) => n.x);
    const ys = nodes.map((n) => n.y);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    setPosition({ x: rect.width / 2 - cx, y: rect.height / 2 - cy });
    hasCenteredRef.current = true;
  }, [nodes, plan?.id, loading, setPosition]);

  useEffect(() => {
    const nodeId = searchParams.get("node");
    if (nodeId && !loading && nodes.length > 0) {
      setSelectedNodeId(nodeId);
    }
  }, [searchParams, loading, nodes.length, setSelectedNodeId]);

  useEffect(() => {
    if (!planId || loading) return;
    const abortController = new AbortController();
    aiApi
      .recommendNext(planId, { signal: abortController.signal })
      .then((data) => {
        if (abortController.signal.aborted) return;
        if (data?.recommended_node_id) {
          setAiRecommendation(data);
        }
      })
      .catch((error) => {
        if (error?.name !== "AbortError") {
          setAiRecommendation(null);
        }
      });
    return () => abortController.abort();
  }, [planId, loading]);

  const [showGoalClarification, setShowGoalClarification] = useState(false);
  const [newGoalInput, setNewGoalInput] = useState("");
  const [clarifyResult, setClarifyResult] = useState(null);
  const [isClarifying, setIsClarifying] = useState(false);
  const [showNoteEditor, setShowNoteEditor] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [noteContent, setNoteContent] = useState("");
  const [resourceSearchLoading, setResourceSearchLoading] = useState({});
  const [resourceSearchFeedback, setResourceSearchFeedback] = useState({});
  const [nodeDeadlineSaving, setNodeDeadlineSaving] = useState({});
  const [nodeDeadlineDraft, setNodeDeadlineDraft] = useState("");
  const minNodeDeadlineDate = useMemo(() => getLocalDateInputValue(), []);
  const isNodeDragging = Boolean(draggingNodeId);

  // F7: per-topic AI explain state: { [`${nodeId}_${i}`]: { loading, content, expanded } }
  const [explainStates, setExplainStates] = useState({});

  useEffect(() => {
    if (!nodes.length) return;

    const preloaded = {};
    for (const node of nodes) {
      const cache = node.contentCache || {};
      for (const [indexStr, text] of Object.entries(cache)) {
        if (text) {
          preloaded[`${node.id}_${indexStr}`] = {
            loading: false,
            content: text,
            expanded: false,
          };
        }
      }
    }

    setExplainStates((prev) => ({ ...preloaded, ...prev }));
  }, [nodes]);

  // F4: contextual chat panel
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatWebSearchEnabled, setChatWebSearchEnabled] = useState(false);
  const [isSavingChatSummary, setIsSavingChatSummary] = useState(false);
  const [chatSummarySaved, setChatSummarySaved] = useState(false);
  const [savingExplainNotes, setSavingExplainNotes] = useState({});
  const [savedExplainNotes, setSavedExplainNotes] = useState({});
  const [chatPanelSize, setChatPanelSize] = useState(() =>
    getDefaultChatPanelSize(
      typeof window === "undefined"
        ? undefined
        : { width: window.innerWidth, height: window.innerHeight },
    ),
  );
  const [isChatResizing, setIsChatResizing] = useState(false);
  const chatEndRef = React.useRef(null);
  const chatMessagesRef = useRef(null);
  const chatResizeStartRef = useRef(null);
  const chatStreamStateRef = useRef({
    content: "",
    sources: [],
    searchStatus: null,
  });
  const chatUpdateRafRef = useRef(null);
  const aiRequestRegistryRef = useRef(createAiRequestRegistry());

  // Scroll chat to bottom on new messages
  useEffect(() => {
    const messageContainer = chatMessagesRef.current;
    if (!messageContainer) return;
    messageContainer.scrollTop = messageContainer.scrollHeight;
  }, [chatMessages, chatLoading]);

  useEffect(
    () => () => {
      if (chatUpdateRafRef.current !== null) {
        cancelAnimationFrame(chatUpdateRafRef.current);
      }
      aiRequestRegistryRef.current.abortAll();
    },
    [],
  );

  // Reset chat when switching nodes
  useEffect(() => {
    aiRequestRegistryRef.current.abortMatching(
      (key) => key.startsWith("chat:") || key.startsWith("explain:"),
    );
    setExplainStates((prev) => {
      const next = {};
      for (const [key, state] of Object.entries(prev)) {
        if (state?.loading && !state?.content) continue;
        next[key] = state?.loading ? { ...state, loading: false } : state;
      }
      return next;
    });
    setChatMessages([]);
    setChatInput("");
    setChatLoading(false);
    setChatWebSearchEnabled(false);
    setIsSavingChatSummary(false);
    setChatSummarySaved(false);
    setSavingExplainNotes({});
    setSavedExplainNotes({});
  }, [selectedNodeId]);

  useEffect(() => {
    setChatSummarySaved(false);
  }, [chatMessages]);

  useEffect(() => {
    if (!masteryProgressStorageKey) {
      setMasteryProgress({});
      return;
    }
    try {
      const raw = window.localStorage.getItem(masteryProgressStorageKey);
      setMasteryProgress(raw ? JSON.parse(raw) : {});
    } catch {
      setMasteryProgress({});
    }
  }, [masteryProgressStorageKey]);

  useEffect(() => {
    const handleWindowResize = () => {
      setChatPanelSize((prev) =>
        clampChatPanelSize(prev, {
          width: window.innerWidth,
          height: window.innerHeight,
        }),
      );
    };

    window.addEventListener("resize", handleWindowResize);
    return () => window.removeEventListener("resize", handleWindowResize);
  }, []);

  useEffect(() => {
    if (!isChatResizing) return undefined;

    const handleMouseMove = (event) => {
      const resizeStart = chatResizeStartRef.current;
      if (!resizeStart) return;

      setChatPanelSize(
        getResizedChatPanelSize(
          resizeStart.size,
          event.clientX - resizeStart.pointerX,
          event.clientY - resizeStart.pointerY,
          {
            width: window.innerWidth,
            height: window.innerHeight,
          },
        ),
      );
    };

    const handleMouseUp = () => {
      setIsChatResizing(false);
      chatResizeStartRef.current = null;
    };

    const previousUserSelect = document.body.style.userSelect;
    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isChatResizing]);

  const nodeNotes = allNotes.filter(
    (n) => n.planId === planId && n.nodeId === selectedNodeId,
  );
  const selectedNodeResources = useMemo(
    () =>
      selectedNode
        ? mergeNodeResources(
            selectedNode.resources,
            selectedNode.resourceSearchCache,
          )
        : [],
    [selectedNode],
  );
  const selectedNodeResourceFeedback = selectedNode
    ? resourceSearchFeedback[selectedNode.id]
    : null;
  const selectedNodeMasteryPassedKeys = useMemo(() => {
    if (!selectedNode?.mastery?.length) return new Set();
    return new Set(
      selectedNode.mastery
        .map((item, index) => buildMasteryCheckKey(selectedNode.id, index, item))
        .filter((key) => masteryProgress[key]?.passed),
    );
  }, [masteryProgress, selectedNode]);
  const selectedNodeDeadlineValue = selectedNode?.targetEndDate
    ? String(selectedNode.targetEndDate).slice(0, 10)
    : "";
  const nodeDeadlineChanged = selectedNode
    ? nodeDeadlineDraft !== selectedNodeDeadlineValue
    : false;
  const selectedNodeExpandedResourceCount = Array.isArray(
    selectedNode?.resourceSearchCache?.items,
  )
    ? selectedNode.resourceSearchCache.items.length
    : 0;
  const searchMoreResourcesLabel = selectedNode
    ? resourceSearchLoading[selectedNode.id]
      ? "搜索中..."
      : selectedNodeResourceFeedback?.added > 0
        ? `已补充 ${selectedNodeResourceFeedback.added} 条资源`
        : selectedNodeExpandedResourceCount > 0
          ? `已扩展 ${selectedNodeExpandedResourceCount} 条资源`
          : "搜索更多资源"
    : "搜索更多资源";

  const handleChatResizeStart = (event) => {
    event.preventDefault();
    event.stopPropagation();

    chatResizeStartRef.current = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      size: chatPanelSize,
    };
    setIsChatResizing(true);
  };

  const learnedCount = nodes.filter((n) => n.status === "learned").length;
  const totalCount = nodes.filter((n) => n.status !== "skipped").length;

  useEffect(() => {
    setGhostNodeIds(
      new Set(
        nodes
          .filter((node) => node._ghost || node.isGhost)
          .map((node) => node.id),
      ),
    );
  }, [nodes]);

  useEffect(() => {
    setNodeDeadlineDraft(selectedNodeDeadlineValue);
  }, [selectedNodeId, selectedNodeDeadlineValue]);

  const nodeMap = useMemo(
    () => new Map(nodes.map((node) => [node.id, node])),
    [nodes],
  );

  const edgeGeometries = useMemo(
    () =>
      edges.flatMap((edge, index) => {
        const from = nodeMap.get(edge.from);
        const to = nodeMap.get(edge.to);
        if (!from || !to) return [];

        return [
          {
            key: `${edge.from}-${edge.to}-${index}`,
            path: buildCurvedEdgePath(from, to, index),
            midpoint: {
              x: (from.x + to.x) / 2,
              y: (from.y + to.y) / 2,
            },
            isTraversed: from.status === "learned",
            isSkipped: from.status === "skipped",
          },
        ];
      }),
    [edges, nodeMap],
  );

  const handleSaveNote = async () => {
    if (noteContent.trim()) {
      try {
        if (editingNoteId) {
          await noteActions.updateNote(editingNoteId, noteContent);
          toast.success("笔记已更新");
        } else {
          await noteActions.addNote(planId, selectedNodeId, noteContent);
          toast.success("笔记已保存");
        }
      } catch {
        return;
      }
    }
    setNoteContent("");
    setEditingNoteId(null);
    setShowNoteEditor(false);
  };

  const openNewNoteEditor = () => {
    setEditingNoteId(null);
    setNoteContent("");
    setShowNoteEditor(true);
  };

  const openEditNoteEditor = (note) => {
    setEditingNoteId(note.id);
    setNoteContent(note.content || "");
    setShowNoteEditor(true);
  };

  const handleCopyPrompt = (prompt) => {
    navigator.clipboard.writeText(prompt);
  };

  const handleSaveExplainNote = async (topicText, topicIndex) => {
    if (!selectedNode) return;

    const explainKey = `${selectedNode.id}_${topicIndex}`;
    if (savingExplainNotes[explainKey]) return;
    const content = explainStates[explainKey]?.content || "";

    setSavingExplainNotes((prev) => ({ ...prev, [explainKey]: true }));
    try {
      const result = await saveExplainNoteToNotes({
        topicText,
        explainContent: content,
        nodeName: selectedNode.name,
        existingNotes: nodeNotes,
        planId,
        selectedNodeId,
        noteActions,
        toast,
      });
      if (result.saved) {
        setSavedExplainNotes((prev) => ({ ...prev, [explainKey]: true }));
      }
    } finally {
      setSavingExplainNotes((prev) => ({ ...prev, [explainKey]: false }));
    }
  };

  const handleSearchMoreResources = async () => {
    if (!selectedNode || !planId) return;

    setResourceSearchLoading((prev) => ({ ...prev, [selectedNode.id]: true }));
    try {
      const result = await graphApi.searchNodeResources(planId, selectedNode.id);
      const nextCache = result.resourceSearchCache || {};
      const resourcesAdded = Number(result.resourcesAdded || 0);

      setNodes((prev) =>
        prev.map((node) =>
          node.id === selectedNode.id
            ? { ...node, resourceSearchCache: nextCache }
            : node,
        ),
      );
      graphActions.updateGraphNodes(planId, (prev) =>
        prev.map((node) =>
          node.id === selectedNode.id
            ? { ...node, resourceSearchCache: nextCache }
            : node,
        ),
      );
      setResourceSearchFeedback((prev) => ({
        ...prev,
        [selectedNode.id]: {
          added: resourcesAdded,
          total: Array.isArray(nextCache.items) ? nextCache.items.length : 0,
          updatedAt: nextCache.updatedAt || null,
        },
      }));

      if (resourcesAdded > 0) {
        toast.success(`已补充 ${resourcesAdded} 条资源`);
      } else {
        toast.info("暂未找到新的高质量资源");
      }
    } catch (error) {
      toast.error(
        error?.message?.includes("写入缓存失败")
          ? error.message
          : "资源搜索失败，请重试",
      );
    } finally {
      setResourceSearchLoading((prev) => ({ ...prev, [selectedNode.id]: false }));
    }
  };

  const handleSaveChatSummary = async () => {
    if (!selectedNode || isSavingChatSummary) return;

    setIsSavingChatSummary(true);
    try {
      const result = await saveChatSummaryToNotes({
        messages: chatMessages,
        nodeName: selectedNode.name,
        existingNotes: nodeNotes,
        planId,
        selectedNodeId,
        noteActions,
        toast,
      });
      if (result.saved) {
        setChatSummarySaved(true);
      }
    } finally {
      setIsSavingChatSummary(false);
    }
  };

  const updateLastAssistantMessage = (patch) => {
    setChatMessages((prev) => {
      if (prev.length === 0) return prev;
      const updated = [...prev];
      updated[updated.length - 1] = {
        ...updated[updated.length - 1],
        role: "assistant",
        ...patch,
      };
      return updated;
    });
  };

  const flushChatMessageNow = () => {
    if (chatUpdateRafRef.current !== null) {
      cancelAnimationFrame(chatUpdateRafRef.current);
      chatUpdateRafRef.current = null;
    }

    updateLastAssistantMessage({ ...chatStreamStateRef.current });
  };

  const scheduleChatMessageFlush = () => {
    if (chatUpdateRafRef.current !== null) return;

    chatUpdateRafRef.current = requestAnimationFrame(() => {
      chatUpdateRafRef.current = null;
      updateLastAssistantMessage({ ...chatStreamStateRef.current });
    });
  };

  const handleClarifyGoal = async () => {
    if (!newGoalInput.trim() || !plan) return;
    setIsClarifying(true);
    try {
      const result = await aiApi.clarifyGoal(plan.title, newGoalInput, planId);
      setClarifyResult(result);
    } catch (err) {
      toast.error("分析失败，请重试");
    } finally {
      setIsClarifying(false);
    }
  };

  const handleApplyClarify = async () => {
    if (!clarifyResult) return;

    if (clarifyResult.isLargeChange) {
      setShowGoalClarification(false);
      setClarifyResult(null);
      navigate(`/?goal=${encodeURIComponent(newGoalInput)}`);
      return;
    }

    try {
      const changes = clarifyResult.changes || {
        keep: [],
        remove: [],
        add: [],
      };
      await graphApi.applyChanges(planId, {
        keep: changes.keep || [],
        remove: changes.remove || [],
        add: changes.add || [],
        newTitle: newGoalInput,
      });
      setShowGoalClarification(false);
      setClarifyResult(null);
      setNewGoalInput("");
      const data = await graphApi.get(planId);
      if (data?.nodes) {
        setNodes(data.nodes);
        setEdges(data.edges || []);
        graphActions.setGraph(planId, {
          title: data.title || null,
          nodes: data.nodes,
          edges: data.edges || [],
        });
      }
      toast.success("目标已更新");
    } catch (err) {
      toast.error("应用修改失败，请重试");
    }
  };

  const handleNodeStatusChange = async (nodeId, newStatus) => {
    const previousNode = nodes.find((node) => node.id === nodeId);
    const previousStatus = previousNode?.status;
    setNodeStatus(nodeId, newStatus);
    try {
      const result = await graphApi.updateNodeStatus(planId, nodeId, newStatus);
      if (result?.plan) {
        actions.updatePlanProgress(planId, result.plan.progress, result.plan.total);
      }
    } catch (err) {
      console.error("Failed to save node status", err);
      if (previousStatus) {
        setNodeStatus(nodeId, previousStatus);
      }
      toast.error("节点状态保存失败，已恢复原状态");
    }
  };

  const handleSaveNodeTargetEndDate = async () => {
    if (!selectedNode) return;
    const nodeId = selectedNode.id;
    if (!planId || !nodeId) return;
    if (!nodeDeadlineChanged) return;

    if (nodeDeadlineDraft && nodeDeadlineDraft < minNodeDeadlineDate) {
      toast.error("节点截止日期不能早于今天");
      return;
    }

    const nextTargetEndDate = nodeDeadlineDraft || null;
    setNodeDeadlineSaving((prev) => ({ ...prev, [nodeId]: true }));

    const applyLocalUpdate = (updater) => {
      setNodes((prev) => prev.map((node) => (node.id === nodeId ? updater(node) : node)));
      graphActions.updateGraphNodes(planId, (prev) =>
        prev.map((node) => (node.id === nodeId ? updater(node) : node)),
      );
    };

    try {
      const result = await graphApi.updateNode(planId, nodeId, {
        targetEndDate: nextTargetEndDate,
      });
      applyLocalUpdate((node) => ({
        ...node,
        targetEndDate: result?.targetEndDate || nextTargetEndDate,
      }));
      setNodeDeadlineDraft(
        result?.targetEndDate ? String(result.targetEndDate).slice(0, 10) : "",
      );
      toast.success(nextTargetEndDate ? "节点截止日期已更新" : "节点截止日期已清除");
    } catch (err) {
      toast.error("节点截止日期保存失败，请重试");
    } finally {
      setNodeDeadlineSaving((prev) => ({ ...prev, [nodeId]: false }));
    }
  };

  const handleResetNodeDeadlineDraft = () => {
    setNodeDeadlineDraft(selectedNodeDeadlineValue);
  };

  const getMasteryItemKey = (item, index, node = selectedNode) =>
    node ? buildMasteryCheckKey(node.id, index, item) : String(index);

  const persistMasteryProgress = (nextProgress) => {
    setMasteryProgress(nextProgress);
    if (!masteryProgressStorageKey) return;
    try {
      window.localStorage.setItem(
        masteryProgressStorageKey,
        JSON.stringify(nextProgress),
      );
    } catch {
      // Local persistence is best-effort; the UI state still updates.
    }
  };

  const handleStartMasteryQuiz = (standard, index) => {
    if (!selectedNode) return;
    const key = getMasteryItemKey(standard, index, selectedNode);
    setMasteryQuiz({
      key,
      nodeId: selectedNode.id,
      nodeName: selectedNode.name,
      index,
      standard,
      questions: generateMasteryQuiz({
        nodeName: selectedNode.name,
        standard,
      }),
    });
  };

  const handleMasteryQuizPassed = ({ key, score, total }) => {
    const nextProgress = {
      ...masteryProgress,
      [key]: {
        passed: true,
        score,
        total,
        passedAt: new Date().toISOString(),
      },
    };
    persistMasteryProgress(nextProgress);
    toast.success("小测通过，掌握标准已打勾");
  };

  const openDateInputPicker = (event) => {
    try {
      event.currentTarget.showPicker?.();
    } catch {
      // Browsers only allow showPicker during direct user gestures.
    }
  };

  const handleDoubleClickNode = (e, nodeId, currentStatus) => {
    e.stopPropagation();
    handleNodeStatusChange(nodeId, toggleNodeStatus(currentStatus));
  };

  const handleSavePlan = async () => {
    const titleToSave = planTitle || plan?.title;
    if (!planId || isSaving || !titleToSave) return;
    setIsSaving(true);
    try {
      await actions.updatePlan(planId, { title: titleToSave });
      setSavedAt(new Date());
      setIsDirty(false);
      toast.success("计划已保存");
    } catch {
      toast.error("保存失败，请重试");
    } finally {
      setIsSaving(false);
    }
  };

  const handlePlanSettingChange = (field, value) => {
    setPlanSettings((prev) => ({ ...prev, [field]: value }));
  };

  const handleSavePlanSettings = async () => {
    if (!planId || isUpdatingPlanSettings) return;
    setIsUpdatingPlanSettings(true);
    try {
      await actions.updatePlan(planId, {
        startDate: planSettings.startDate || null,
        targetEndDate: planSettings.targetEndDate || null,
        studyFrequency: planSettings.studyFrequency,
        studyDaysPerWeek: Number(planSettings.studyDaysPerWeek) || 3,
        reminderEnabled: planSettings.reminderEnabled,
        reminderTime: planSettings.reminderEnabled
          ? planSettings.reminderTime || null
          : null,
        reminderTimezone: planSettings.reminderEnabled
          ? planSettings.reminderTimezone || null
          : null,
      });
      setShowPlanSettings(false);
      toast.success("学习计划设置已更新");
    } catch (error) {
      toast.error("更新计划设置失败");
    } finally {
      setIsUpdatingPlanSettings(false);
    }
  };

  const handlePauseOrResumePlan = async () => {
    if (!planId || !plan || isTogglingPlanStatus) return;
    setIsTogglingPlanStatus(true);
    try {
      if (plan.status === "paused") {
        await actions.resumePlan(planId);
        toast.success("计划已恢复");
      } else {
        await actions.pausePlan(planId);
        toast.success("计划已暂停");
      }
    } catch (error) {
      // Toast handled in context.
    } finally {
      setIsTogglingPlanStatus(false);
    }
  };

  const handleSharePlan = async () => {
    if (!planId || isSharingPlan) return;
    setIsSharingPlan(true);
    const shareUrl = `${window.location.origin}/graph/${planId}`;
    const shareTitle = planTitle || plan?.title || "学习计划";
    try {
      if (navigator.share) {
        await navigator.share({
          title: shareTitle,
          text: `查看我的学习计划：${shareTitle}`,
          url: shareUrl,
        });
        toast.success("分享面板已打开");
        return;
      }

      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl);
        toast.success("计划链接已复制");
        return;
      }

      toast.error("当前环境暂不支持分享，请手动复制地址栏链接");
    } catch (error) {
      if (error?.name !== "AbortError") {
        toast.error("分享失败，请重试");
      }
    } finally {
      setIsSharingPlan(false);
    }
  };

  // F7: click a what-item -> stream AI explanation
  const handleExplainTopic = async (topicText, topicIndex) => {
    if (!selectedNode) return;
    const key = `${selectedNode.id}_${topicIndex}`;
    const requestKey = `explain:${planId}:${selectedNode.id}:${topicIndex}`;
    const nodeId = selectedNode.id;
    const current = explainStates[key];

    if (current?.loading) return;

    // Toggle off if already loaded
    if (current?.content) {
      setExplainStates((prev) => ({
        ...prev,
        [key]: { ...prev[key], expanded: !prev[key].expanded },
      }));
      return;
    }

    const request = aiRequestRegistryRef.current.begin(requestKey, { dedupe: true });
    if (request.deduped) return;

    setExplainStates((prev) => ({ ...prev, [key]: { loading: true, content: "", expanded: true } }));

    try {
      let accumulated = "";
      await aiApi.explainTopic(
        nodeId,
        topicIndex,
        topicText,
        {
          nodeName: selectedNode.name,
          why: selectedNode.why,
          planTitle: planTitle || plan?.title,
        },
        (chunk) => {
          if (!aiRequestRegistryRef.current.isCurrent(requestKey, request.requestId)) return;
          accumulated += chunk;
          setExplainStates((prev) => ({
            ...prev,
            [key]: { loading: false, content: accumulated, expanded: true },
          }));
        },
        { signal: request.signal },
      );
      if (
        request.signal.aborted ||
        !aiRequestRegistryRef.current.isCurrent(requestKey, request.requestId)
      ) {
        return;
      }
      // Ensure loading is cleared even if no chunks arrived.
      setExplainStates((prev) => ({
        ...prev,
        [key]: {
          loading: false,
          content: prev[key]?.content || "内容生成为空，请重试。",
          expanded: true,
        },
      }));
      if (accumulated) {
        setNodes((prev) =>
          prev.map((node) =>
            node.id === nodeId
              ? {
                  ...node,
                  contentCache: {
                    ...(node.contentCache || {}),
                    [topicIndex]: accumulated,
                  },
                }
              : node,
          ),
        );
        graphActions.updateGraphNodes(planId, (prev) =>
          prev.map((node) =>
            node.id === nodeId
              ? {
                  ...node,
                  contentCache: {
                    ...(node.contentCache || {}),
                    [topicIndex]: accumulated,
                  },
                }
              : node,
          ),
        );
      }
    } catch (err) {
      if (err?.name === "AbortError") return;
      if (!aiRequestRegistryRef.current.isCurrent(requestKey, request.requestId)) return;
      console.error("[explainTopic] error:", err);
      setExplainStates((prev) => ({
        ...prev,
        [key]: { loading: false, content: "解释生成失败，请重试。", expanded: true },
      }));
    } finally {
      aiRequestRegistryRef.current.finish(requestKey, request.requestId);
    }
  };

  // F4: send chat message
  const handleChatSend = async () => {
    if (!chatInput.trim() || chatLoading || !selectedNode) return;

    const userMsg = { role: "user", content: chatInput.trim() };
    const conversationMessages = [...chatMessages, userMsg];
    const assistantPlaceholder = {
      role: "assistant",
      content: "",
      sources: [],
      searchStatus: chatWebSearchEnabled ? "searching" : null,
    };

    chatStreamStateRef.current = {
      content: "",
      sources: [],
      searchStatus: assistantPlaceholder.searchStatus,
    };

    setChatMessages([...conversationMessages, assistantPlaceholder]);
    setChatInput("");
    setChatLoading(true);

    const requestKey = `chat:${planId}:${selectedNode.id}`;
    const request = aiRequestRegistryRef.current.begin(requestKey);

    try {
      await aiApi.chatStream(
        conversationMessages,
        {
          nodeName: selectedNode.name,
          why: selectedNode.why,
          planTitle: planTitle || plan?.title,
        },
        {
          enableWebSearch: chatWebSearchEnabled,
          onChunk: (chunk) => {
            if (!aiRequestRegistryRef.current.isCurrent(requestKey, request.requestId)) return;
            chatStreamStateRef.current = {
              ...chatStreamStateRef.current,
              content: `${chatStreamStateRef.current.content}${chunk}`,
            };
            scheduleChatMessageFlush();
          },
          onSources: (sources) => {
            if (!aiRequestRegistryRef.current.isCurrent(requestKey, request.requestId)) return;
            chatStreamStateRef.current = {
              ...chatStreamStateRef.current,
              sources,
            };
            scheduleChatMessageFlush();
          },
          onSearchStatus: (status) => {
            if (!aiRequestRegistryRef.current.isCurrent(requestKey, request.requestId)) return;
            chatStreamStateRef.current = {
              ...chatStreamStateRef.current,
              searchStatus: status,
            };
            scheduleChatMessageFlush();
          },
          signal: request.signal,
        },
      );
      if (
        request.signal.aborted ||
        !aiRequestRegistryRef.current.isCurrent(requestKey, request.requestId)
      ) {
        return;
      }

      if (!chatStreamStateRef.current.content) {
        chatStreamStateRef.current = {
          ...chatStreamStateRef.current,
          content: "内容生成为空，请重试。",
        };
      }

      flushChatMessageNow();
    } catch (err) {
      if (err?.name === "AbortError") return;
      if (!aiRequestRegistryRef.current.isCurrent(requestKey, request.requestId)) return;
      chatStreamStateRef.current = {
        ...chatStreamStateRef.current,
        content: "回复失败，请重试。",
        searchStatus:
          chatStreamStateRef.current.searchStatus === "searching"
            ? "fallback"
            : chatStreamStateRef.current.searchStatus,
      };
      flushChatMessageNow();
    } finally {
      if (aiRequestRegistryRef.current.isCurrent(requestKey, request.requestId)) {
        aiRequestRegistryRef.current.finish(requestKey, request.requestId);
        setChatLoading(false);
      }
    }
  };

  const handleNavigateBack = () => {
    if (isDirty) {
      setShowLeaveConfirm(true);
    } else {
      navigate("/");
    }
  };

  const flushPendingNodePositions = () => {
    if (!planId || pendingNodePositionsRef.current.size === 0) return;
    const positions = Array.from(pendingNodePositionsRef.current.values());
    pendingNodePositionsRef.current.clear();

    graphApi.updateNodePositions(planId, positions).catch((err) => {
      console.error("Failed to save node positions", err);
      toast.error("节点位置同步失败，稍后会以当前画布为准");
    });
  };

  const scheduleNodePositionSave = (id, x, y) => {
    if (!id) return;
    pendingNodePositionsRef.current.set(id, { nodeId: id, x, y });
    if (positionSaveTimerRef.current) {
      clearTimeout(positionSaveTimerRef.current);
    }
    positionSaveTimerRef.current = setTimeout(() => {
      positionSaveTimerRef.current = null;
      flushPendingNodePositions();
    }, 500);
  };

  const handleContainerMouseMove = (e) => {
    handleMouseMove(e, containerRef);
    if (draggingNodeId && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const viewport = viewportRef.current;
      draggingPosRef.current = {
        id: draggingNodeId,
        x: (e.clientX - rect.left - viewport.position.x) / viewport.scale,
        y: (e.clientY - rect.top - viewport.position.y) / viewport.scale,
      };
    }
  };

  const handleContainerMouseUp = () => {
    const { id, x, y } = draggingPosRef.current;
    handleMouseUp();
    if (id) {
      scheduleNodePositionSave(id, x, y);
      draggingPosRef.current = { id: null, x: 0, y: 0 };
    }
  };

  const handleRelayoutGraph = () => {
    if (!nodes.length) return;
    const targetNode = nodes.find((node) => node.isTarget);
    const targetNodeId = targetNode?.id || plan?.targetNodeId || nodes[nodes.length - 1]?.id;
    const positions = calculateLayout(nodes, edges, targetNodeId);
    const nextNodes = nodes.map((node) => ({
      ...node,
      x: positions[node.id]?.x ?? node.x,
      y: positions[node.id]?.y ?? node.y,
    }));

    setNodes(nextNodes);
    graphActions.setGraph(planId, {
      title: planTitle || plan?.title || null,
      nodes: nextNodes,
      edges,
    });

    if (planId) {
      graphApi
        .updateNodePositions(
          planId,
          nextNodes.map((node) => ({ nodeId: node.id, x: node.x, y: node.y })),
        )
        .catch((err) => {
          console.error("Failed to save relayout", err);
          toast.error("路径布局已更新，位置同步稍后会重试");
        });
    }

    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const xs = nextNodes.map((node) => node.x);
      const ys = nextNodes.map((node) => node.y);
      const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
      const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
      setPosition({ x: rect.width / 2 - cx, y: rect.height / 2 - cy });
    }
  };

  if (!plan && !loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#FAFAFA]">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-zinc-900 mb-2">
            未找到学习计划
          </h2>
          <Button onClick={() => navigate("/")}>返回首页</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#F4F4F5] relative overflow-hidden">
      {/* Top Navigation */}
      <div className="absolute top-0 left-0 right-0 z-20 px-6 py-4 pointer-events-none">
        <div className="max-w-screen-xl mx-auto flex justify-between items-start">
          <div className="bg-white/90 backdrop-blur-md px-5 py-3 rounded-2xl shadow-sm border border-zinc-200/50 pointer-events-auto flex items-center gap-4 transition-all hover:shadow-md">
            <button
              onClick={handleNavigateBack}
              className="text-zinc-400 hover:text-zinc-900 transition-colors"
            >
              <ArrowLeft size={20} strokeWidth={1.5} />
            </button>
            <div className="h-4 w-px bg-zinc-200" />
            <div>
              <h1 className="text-sm font-semibold text-zinc-800">
                {planTitle || plan?.title || "加载中..."}
              </h1>
              <div className="flex items-center gap-2 mt-0.5">
                <div className="h-1 w-16 bg-zinc-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-teal-600 rounded-full transition-all duration-500"
                    style={{
                      width:
                        totalCount > 0
                          ? `${(learnedCount / totalCount) * 100}%`
                          : "0%",
                    }}
                  />
                </div>
                <span className="text-[10px] text-zinc-400 font-medium tracking-wide">
                  {learnedCount}/{totalCount} 已掌握
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-1 text-[10px] font-medium text-zinc-500">
                  <CalendarDays size={11} />
                  {getPlanFrequencyLabel(plan?.studyFrequency, plan?.studyDaysPerWeek)}
                </span>
                {plan?.targetEndDate ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-[10px] font-medium text-amber-700">
                    截止 {formatPlanDateLabel(plan.targetEndDate)}
                  </span>
                ) : null}
                {plan?.reminderEnabled ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-1 text-[10px] font-medium text-teal-700">
                    <Bell size={11} />
                    {plan?.reminderTime || "已开启提醒"}
                  </span>
                ) : null}
                {plan?.status === "paused" ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-2 py-1 text-[10px] font-medium text-white">
                    已暂停
                  </span>
                ) : null}
                {plan?.status === "archived" ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-2 py-1 text-[10px] font-medium text-white">
                    已归档
                  </span>
                ) : null}
              </div>
            </div>
          </div>

          <div className="bg-white/90 backdrop-blur-md p-2 rounded-2xl shadow-sm border border-zinc-200/50 pointer-events-auto flex gap-1 items-center">
            {savedAt && !isDirty ? (
              <span className="text-[10px] text-zinc-400 px-2">
                已保存于{" "}
                {savedAt.toLocaleTimeString("zh-CN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            ) : isDirty ? (
              <button
                onClick={handleSavePlan}
                disabled={isSaving}
                className="px-3 py-1.5 text-xs font-medium text-white bg-zinc-900 rounded-xl hover:bg-zinc-700 transition-colors disabled:opacity-50 flex items-center gap-1.5"
              >
                <Save size={12} />
                {isSaving ? "保存中..." : "保存计划"}
              </button>
            ) : null}
            <button
              className="p-2 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-50 rounded-xl transition-all"
              title="计划设置"
              onClick={() => setShowPlanSettings(true)}
            >
              <SlidersHorizontal size={18} strokeWidth={1.5} />
            </button>
            {plan?.status !== "archived" ? (
              <button
                className={`p-2 rounded-xl transition-all disabled:opacity-50 ${
                  plan?.status === "paused"
                    ? "bg-zinc-900 text-white hover:bg-zinc-700"
                    : "text-zinc-400 hover:text-zinc-900 hover:bg-zinc-50"
                }`}
                title={plan?.status === "paused" ? "恢复计划" : "暂停计划"}
                onClick={handlePauseOrResumePlan}
                disabled={isTogglingPlanStatus}
              >
                {isTogglingPlanStatus ? (
                  <Loader size={18} className="animate-spin" strokeWidth={1.5} />
                ) : plan?.status === "paused" ? (
                  <Play size={18} strokeWidth={1.5} />
                ) : (
                  <Pause size={18} strokeWidth={1.5} />
                )}
              </button>
            ) : null}
            <button
              className={`p-2 rounded-xl transition-all disabled:opacity-50 ${
                isSharingPlan
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-400 hover:text-zinc-900 hover:bg-zinc-50"
              }`}
              title="分享"
              onClick={handleSharePlan}
              disabled={isSharingPlan}
            >
              {isSharingPlan ? (
                <Loader size={18} className="animate-spin" strokeWidth={1.5} />
              ) : (
                <Share2 size={18} strokeWidth={1.5} />
              )}
            </button>
            <button
              className="p-2 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-50 rounded-xl transition-all"
              title="修改目标"
              onClick={() => {
                setNewGoalInput("");
                setClarifyResult(null);
                setShowGoalClarification(true);
              }}
            >
              <Edit3 size={18} strokeWidth={1.5} />
            </button>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div
        className="flex-1 relative overflow-hidden cursor-grab active:cursor-grabbing"
        ref={containerRef}
        onMouseDown={(e) => handleMouseDown(e, containerRef)}
        onMouseMove={handleContainerMouseMove}
        onMouseUp={handleContainerMouseUp}
        onMouseLeave={handleContainerMouseUp}
        onWheel={handleWheel}
      >
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: `radial-gradient(#000 1px, transparent 1px)`,
            backgroundSize: `${24 * scale}px ${24 * scale}px`,
            backgroundPosition: `${position.x}px ${position.y}px`,
          }}
        />

        <div
          className="absolute top-0 left-0 w-full h-full origin-top-left will-change-transform"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
          }}
        >
          {/* Edges */}
          <svg className="absolute top-0 left-0 overflow-visible w-full h-full pointer-events-none">
            {edgeGeometries.map((edge) => (
              <g key={edge.key}>
                <path
                  d={edge.path}
                  fill="none"
                  stroke={edge.isTraversed ? "rgba(13, 148, 136, 0.14)" : "rgba(113, 113, 122, 0.08)"}
                  strokeWidth={edge.isTraversed ? 6 : 5}
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
                <path
                  d={edge.path}
                  fill="none"
                  stroke={edge.isTraversed ? "#0D9488" : "#A1A1AA"}
                  strokeOpacity={edge.isTraversed ? 0.8 : 0.72}
                  strokeWidth={edge.isTraversed ? 2.2 : 1.6}
                  strokeLinecap="round"
                  strokeDasharray={edge.isSkipped ? "5,6" : undefined}
                  vectorEffect="non-scaling-stroke"
                />
                {edge.isTraversed && (
                  <circle
                    cx={edge.midpoint.x}
                    cy={edge.midpoint.y}
                    r={2.4}
                    fill="#0D9488"
                  />
                )}
              </g>
            ))}
            {false && edges.map((edge, i) => {
              const from = nodes.find((n) => n.id === edge.from);
              const to = nodes.find((n) => n.id === edge.to);
              if (!from || !to) return null;

              const isTraversed = from.status === "learned";
              return (
                <g key={i}>
                  <line
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke={isTraversed ? "#0D9488" : "#A1A1AA"}
                    strokeWidth={isTraversed ? 2 : 1.5}
                    strokeDasharray={from.status === "skipped" ? "4,4" : "0"}
                  />
                  {isTraversed && (
                    <circle
                      cx={(from.x + to.x) / 2}
                      cy={(from.y + to.y) / 2}
                      r={2}
                      fill="#0D9488"
                    />
                  )}
                </g>
              );
            })}
          </svg>

          {/* Nodes */}
          {nodes.map((node) => {
            const isSelected = selectedNodeId === node.id;
            const isLearned = node.status === "learned";
            const isGhost = ghostNodeIds.has(node.id);
            return (
              <div
                key={node.id}
                className={`absolute transform -translate-x-1/2 -translate-y-1/2 flex items-center justify-center cursor-pointer
                  ${scale < 0.6 ? "w-4 h-4 rounded-full" : "w-auto h-auto px-6 py-3 rounded-full"}
                  ${isNodeDragging ? "transition-none" : "transition-[opacity,transform,box-shadow,border-color,background-color,color] duration-300"}
                  ${isSelected ? "scale-110 shadow-[0_10px_40px_rgba(0,0,0,0.15)] z-10" : "shadow-[0_2px_12px_rgba(0,0,0,0.1)] hover:shadow-[0_4px_20px_rgba(0,0,0,0.15)] z-0"}
                  ${isLearned ? "bg-zinc-900 text-white border border-zinc-700" : "bg-white text-zinc-800 border border-zinc-300 hover:border-zinc-400"}
                  ${node.isTarget && !isLearned ? "ring-2 ring-teal-500/30 border-teal-500 text-teal-700 bg-teal-50" : ""}
                  ${isGhost ? "opacity-[0.45] scale-[0.97]" : "opacity-100"}
                `}
                style={{ left: node.x, top: node.y }}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedNodeId(node.id);
                }}
                onDoubleClick={(e) =>
                  handleDoubleClickNode(e, node.id, node.status)
                }
                onMouseDown={(e) => {
                  e.stopPropagation();
                  setDraggingNodeId(node.id);
                }}
              >
                {scale < 0.6 ? (
                  isGhost ? (
                    <div className="h-2.5 w-2.5 animate-spin rounded-full border border-zinc-200 border-t-blue-400" />
                  ) : isLearned ? (
                    <div className="w-2 h-2 bg-emerald-400 rounded-full" />
                  ) : (
                    <div className="w-2 h-2 bg-zinc-400 rounded-full" />
                  )
                ) : (
                  <div className="flex items-center gap-3">
                    {isGhost ? (
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-200 border-t-blue-400" />
                    ) : isLearned ? (
                      <CheckCircle2
                        size={16}
                        className="text-emerald-400"
                        strokeWidth={2.5}
                      />
                    ) : node.isTarget ? (
                      <Target size={16} className="text-teal-500" />
                    ) : (
                      <Circle
                        size={16}
                        className="text-zinc-400"
                        strokeWidth={2}
                      />
                    )}
                    <span
                      className={`text-sm font-medium tracking-wide whitespace-nowrap ${node.status === "skipped" ? "line-through opacity-50" : ""}`}
                    >
                      {node.name}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Floating Recommendation / Completion */}
      {(() => {
        if (!loading && isAllComplete(nodes)) {
          return (
            <div className="absolute bottom-12 left-1/2 transform -translate-x-1/2 bg-white/90 backdrop-blur-md shadow-[0_8px_30px_rgba(0,0,0,0.08)] border border-zinc-100 rounded-full px-6 py-3 flex items-center gap-3 z-10">
              <span className="text-xl">🎉</span>
              <span className="text-sm font-semibold text-zinc-800">
                学习完成！
              </span>
            </div>
          );
        }
        if (!recommendedNode) return null;
        if (selectedNodeId) {
          return (
            <div
              className="absolute bottom-12 left-1/2 transform -translate-x-1/2 bg-white/80 backdrop-blur-md shadow-sm border border-zinc-100 rounded-full px-4 py-2 flex items-center gap-2 z-10 cursor-pointer opacity-60 hover:opacity-100 transition-opacity"
              onClick={() => setSelectedNodeId(recommendedNode.id)}
            >
              <span className="text-sm">✨</span>
              <span className="text-xs font-medium text-zinc-600">
                {recommendedNode.name}
              </span>
            </div>
          );
        }
        return (
          <div
            className="absolute bottom-12 left-1/2 transform -translate-x-1/2 bg-white/90 backdrop-blur-md shadow-[0_8px_30px_rgba(0,0,0,0.08)] border border-zinc-100 rounded-full pl-2 pr-6 py-2 flex items-center gap-4 z-10 transition-transform hover:-translate-y-1 hover:shadow-xl cursor-pointer"
            onClick={() => setSelectedNodeId(recommendedNode.id)}
          >
            <div className="w-8 h-8 rounded-full bg-teal-50 flex items-center justify-center text-teal-600">
              <Sparkles size={14} fill="currentColor" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                推荐下一步
              </span>
              <span className="text-sm font-semibold text-zinc-800">
                {recommendedNode.name}
              </span>
              {recommendedNode.recommendReason && (
                <span className="text-[11px] text-zinc-400 mt-0.5 max-w-[200px] truncate">
                  {recommendedNode.recommendReason}
                </span>
              )}
            </div>
            <ChevronRight size={16} className="text-zinc-400 ml-2" />
          </div>
        );
      })()}

      {/* Zoom Controls */}
      <div className="absolute bottom-8 right-8 flex flex-col gap-3 z-10">
        <div className="bg-white/90 backdrop-blur rounded-2xl shadow-sm border border-zinc-200/50 p-1.5 flex flex-col gap-1">
          <button
            onClick={zoomIn}
            className="p-2.5 hover:bg-zinc-50 rounded-xl text-zinc-500 transition-colors"
          >
            <Plus size={18} strokeWidth={1.5} />
          </button>
          <div className="h-px bg-zinc-100 w-full" />
          <button
            onClick={zoomOut}
            className="p-2.5 hover:bg-zinc-50 rounded-xl text-zinc-500 transition-colors"
          >
            <Minus size={18} strokeWidth={1.5} />
          </button>
        </div>
        <button
          onClick={handleRelayoutGraph}
          title="按学习路径整理布局"
          className="bg-white/90 backdrop-blur p-4 rounded-2xl shadow-sm border border-zinc-200/50 text-zinc-500 hover:text-zinc-900 transition-colors"
        >
          <Sparkles size={18} strokeWidth={1.5} />
        </button>
        <button
          onClick={() => {
            if (containerRef.current && nodes.length > 0) {
              const rect = containerRef.current.getBoundingClientRect();
              const xs = nodes.map(n => n.x);
              const ys = nodes.map(n => n.y);
              const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
              const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
              setPosition({ x: rect.width / 2 - cx, y: rect.height / 2 - cy });
            } else {
              resetView();
            }
          }}
          className="bg-white/90 backdrop-blur p-4 rounded-2xl shadow-sm border border-zinc-200/50 text-zinc-500 hover:text-zinc-900 transition-colors"
        >
          <RotateCcw size={18} strokeWidth={1.5} />
        </button>
      </div>

      {/* Node Detail Drawer */}
      <div
        className={`absolute top-4 right-4 bottom-4 w-[400px] bg-white/95 backdrop-blur-2xl shadow-[0_0_50px_rgba(0,0,0,0.05)] rounded-3xl border border-zinc-100 transform transition-transform duration-500 cubic-bezier(0.16, 1, 0.3, 1) flex flex-col z-30 ${selectedNodeId ? "translate-x-0" : "translate-x-[calc(100%+2rem)]"}`}
      >
        {selectedNode && (
          <>
            <div className="px-8 py-8 border-b border-zinc-50 flex justify-between items-start">
              <div>
                  <span className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2 block">
                    知识节点
                  </span>
                <h2 className="text-2xl font-semibold text-zinc-900 leading-tight">
                  {selectedNode.name}
                </h2>
              </div>
              <button
                onClick={() => setSelectedNodeId(null)}
                className="p-2 -mr-2 text-zinc-300 hover:text-zinc-600 transition-colors rounded-full hover:bg-zinc-50"
              >
                <X size={24} strokeWidth={1.5} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-8 py-6 space-y-10 custom-scrollbar">
              {/* Actions */}
              <div className="flex gap-3">
                {selectedNode.status === "learned" ? (
                  <Button
                    variant="secondary"
                    className="flex-1 border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100"
                    onClick={() =>
                      handleNodeStatusChange(selectedNode.id, "unlearned")
                    }
                  >
                    <Check size={16} className="mr-2" /> 已学习
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    className="flex-1 shadow-none"
                    onClick={() =>
                      handleNodeStatusChange(selectedNode.id, "learned")
                    }
                  >
                    标记已学
                  </Button>
                )}
                <Button
                  variant="secondary"
                  className="px-3"
                  onClick={() =>
                    handleNodeStatusChange(
                      selectedNode.id,
                      selectedNode.status === "skipped"
                        ? "unlearned"
                        : "skipped",
                    )
                  }
                >
                  {selectedNode.status === "skipped" ? (
                    <RotateCcw size={16} />
                  ) : (
                    <Minus size={16} />
                  )}
                </Button>
              </div>
              {selectedNode.what?.length > 0 && (
                <Button
                  variant="secondary"
                  className="w-full border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
                  onClick={() => navigate(`/deep-learn/${planId}/${selectedNode.id}`)}
                >
                  <Sparkles size={16} className="mr-2" /> 深入学习
                </Button>
              )}

              <div className="rounded-2xl border border-zinc-100 bg-zinc-50/70 p-4">
                <label className="flex items-center justify-between gap-4">
                  <span className="flex items-center gap-2 text-xs font-medium text-zinc-500">
                    <CalendarDays size={14} /> 节点截止日期
                  </span>
                  {nodeDeadlineSaving[selectedNode.id] ? (
                    <span className="flex items-center gap-1 text-[11px] text-teal-500">
                      <Loader size={12} className="animate-spin" /> 保存中
                    </span>
                  ) : null}
                </label>
                <div className="mt-3 flex gap-2">
                  <input
                    type="date"
                    min={minNodeDeadlineDate}
                    inputMode="none"
                    className="min-w-0 flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none transition-colors focus:border-zinc-400"
                    value={nodeDeadlineDraft}
                    onChange={(event) => setNodeDeadlineDraft(event.target.value)}
                    onBeforeInput={(event) => event.preventDefault()}
                    onKeyDown={(event) => event.preventDefault()}
                    onPaste={(event) => event.preventDefault()}
                    onDrop={(event) => event.preventDefault()}
                    onFocus={openDateInputPicker}
                    onClick={openDateInputPicker}
                    title="请通过日历选择今天或之后的日期"
                  />
                  {nodeDeadlineDraft ? (
                    <button
                      type="button"
                      onClick={() => setNodeDeadlineDraft("")}
                      disabled={Boolean(nodeDeadlineSaving[selectedNode.id])}
                      className="rounded-xl border border-zinc-200 bg-white px-3 text-xs font-medium text-zinc-500 transition-colors hover:border-zinc-300 hover:text-zinc-700"
                    >
                      清除
                    </button>
                  ) : null}
                  {nodeDeadlineChanged ? (
                    <button
                      type="button"
                      onClick={handleResetNodeDeadlineDraft}
                      disabled={Boolean(nodeDeadlineSaving[selectedNode.id])}
                      className="rounded-xl border border-zinc-200 bg-white px-3 text-xs font-medium text-zinc-500 transition-colors hover:border-zinc-300 hover:text-zinc-700"
                    >
                      取消
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={handleSaveNodeTargetEndDate}
                    disabled={
                      Boolean(nodeDeadlineSaving[selectedNode.id]) ||
                      !nodeDeadlineChanged ||
                      Boolean(nodeDeadlineDraft && nodeDeadlineDraft < minNodeDeadlineDate)
                    }
                    className="rounded-xl bg-zinc-900 px-4 text-xs font-medium text-white transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    {nodeDeadlineSaving[selectedNode.id] ? "保存中" : "保存"}
                  </button>
                </div>
                {nodeDeadlineDraft && nodeDeadlineDraft < minNodeDeadlineDate ? (
                  <p className="mt-2 text-xs text-red-500">
                    只能选择今天或之后的日期。
                  </p>
                ) : selectedNode.targetEndDate ? (
                  <p className="mt-2 text-xs text-zinc-400">
                    当前截止日期：{formatPlanDateLabel(selectedNode.targetEndDate)}
                  </p>
                ) : (
                  <p className="mt-2 text-xs text-zinc-400">
                    选择日期后点击保存才会生效。
                  </p>
                )}
              </div>

              <div className="space-y-6">
                {selectedNode.why && (
                  <InfoSection icon={Target} title="为什么学">
                    {selectedNode.why}
                    {edges
                      .filter((e) => e.from === selectedNode.id)
                      .map((e) => {
                        const target = nodes.find((n) => n.id === e.to);
                        if (!target) return null;
                        return (
                          <button
                            key={e.to}
                            onClick={() => setSelectedNodeId(e.to)}
                            className="mt-2 flex items-center gap-1 text-xs text-teal-600 hover:text-teal-800 transition-colors"
                          >
                            <ChevronRight size={12} />
                            用于：{target.name}
                          </button>
                        );
                      })}
                  </InfoSection>
                )}

                {selectedNode.what?.length > 0 && (
                  <section>
                    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                      <BookOpen size={14} /> 核心内容
                      <span className="text-[10px] font-normal text-teal-500 ml-1">点击主题获取 AI 解释</span>
                    </h4>
                    <ul className="space-y-3">
                      {selectedNode.what.map((item, i) => {
                        const key = `${selectedNode.id}_${i}`;
                        const state = explainStates[key];
                        const isSavingExplainNote = Boolean(savingExplainNotes[key]);
                        const isExplainSaved = Boolean(savedExplainNotes[key]);
                        return (
                          <li key={i} className="text-sm text-zinc-600">
                            <button
                              className="flex items-start gap-3 w-full text-left group hover:text-teal-700 transition-colors"
                              onClick={() => handleExplainTopic(item, i)}
                            >
                              <div className="w-1.5 h-1.5 rounded-full bg-zinc-200 mt-2 group-hover:bg-teal-500 transition-colors flex-shrink-0" />
                              <span className="leading-relaxed flex-1">{item}</span>
                              {state?.loading ? (
                                <Loader size={12} className="mt-1.5 text-teal-400 animate-spin flex-shrink-0" />
                              ) : state?.content ? (
                                <ChevronDown
                                  size={12}
                                  className={`mt-1.5 text-teal-400 flex-shrink-0 transition-transform ${state.expanded ? "rotate-180" : ""}`}
                                />
                              ) : (
                                <Sparkles size={12} className="mt-1.5 text-zinc-300 group-hover:text-teal-400 flex-shrink-0 transition-colors" />
                              )}
                            </button>
                            {state?.expanded && state?.content && (
                              <div className="ml-4 mt-3 rounded-2xl border border-teal-100/90 bg-gradient-to-br from-teal-50 via-white to-cyan-50 p-4 shadow-[0_12px_32px_rgba(20,184,166,0.08)]">
                                <div className="mb-3 flex items-center justify-between gap-3">
                                  <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-teal-500">
                                    AI 解释
                                  </span>
                                  <button
                                    type="button"
                                    aria-label={`保存主题“${item}”到笔记`}
                                    onClick={() => handleSaveExplainNote(item, i)}
                                    disabled={isSavingExplainNote}
                                    className="inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-white/80 px-3 py-1.5 text-[11px] font-medium text-teal-700 transition-colors hover:border-teal-300 hover:text-teal-900 disabled:cursor-not-allowed disabled:opacity-50"
                                  >
                                    {isSavingExplainNote ? (
                                      <Loader size={12} className="animate-spin" />
                                    ) : (
                                      <Save size={12} />
                                    )}
                                    {isSavingExplainNote
                                      ? "保存中..."
                                      : isExplainSaved
                                        ? "已保存"
                                        : "保存到笔记"}
                                  </button>
                                </div>
                                <MarkdownContent content={state.content} />
                              </div>
                            )}
                            {state?.loading && (
                              <div className="ml-4 mt-2 p-3 bg-zinc-50 border border-zinc-100 rounded-xl text-xs text-zinc-400 animate-pulse">
                                AI 正在生成解释...
                              </div>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </section>
                )}

                {selectedNode.mastery?.length > 0 && (
                  <MasteryChecklist
                    items={selectedNode.mastery}
                    passedKeys={selectedNodeMasteryPassedKeys}
                    getItemKey={(item, index) =>
                      getMasteryItemKey(item, index, selectedNode)
                    }
                    onStartQuiz={handleStartMasteryQuiz}
                  />
                )}

                {selectedNode.prompt && (
                  <InfoSection icon={Sparkles} title="学习 Prompt">
                    <div className="relative group">
                      <p className="text-sm font-mono bg-zinc-100/50 p-3 rounded-lg text-zinc-600">
                        {selectedNode.prompt}
                      </p>
                      <button
                        onClick={() => handleCopyPrompt(selectedNode.prompt)}
                        className="absolute top-2 right-2 p-1.5 bg-white shadow-sm border border-zinc-200 rounded text-zinc-400 hover:text-zinc-900 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Copy size={12} />
                      </button>
                    </div>
                  </InfoSection>
                )}

                {selectedNodeResources.length > 0 && (
                  <ResourceList resources={selectedNodeResources} />
                )}

                <button
                  onClick={handleSearchMoreResources}
                  disabled={Boolean(resourceSearchLoading[selectedNode.id])}
                  className={`w-full rounded-xl border px-4 py-3 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                    selectedNodeExpandedResourceCount > 0
                      ? "border-teal-200 bg-teal-50/60 text-teal-700 hover:border-teal-300 hover:text-teal-800"
                      : "border-dashed border-zinc-200 text-zinc-400 hover:border-zinc-300 hover:text-zinc-600"
                  }`}
                >
                  <span className="block font-medium">{searchMoreResourcesLabel}</span>
                  {selectedNodeExpandedResourceCount > 0 && !resourceSearchLoading[selectedNode.id] && (
                    <span className="mt-1 block text-[11px] text-zinc-400">
                      {hasExpandedResources(selectedNode.resourceSearchCache)
                        ? "刷新页面后也会保留这些扩展资源"
                        : ""}
                    </span>
                  )}
                </button>

                {/* Notes */}
                <section>
                  <div className="flex justify-between items-center mb-4">
                    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
                      <FileText size={14} /> 笔记
                    </h4>
                    <button
                      onClick={openNewNoteEditor}
                      className="text-xs font-medium text-teal-600 hover:text-teal-800 transition-colors"
                    >
                      + 添加
                    </button>
                  </div>
                  <div className="space-y-3">
                    {nodeNotes.length > 0 ? (
                      nodeNotes.map((note) => (
                        <div
                          key={note.id}
                          onClick={() => openEditNoteEditor(note)}
                          className="group cursor-pointer bg-amber-50/50 border border-amber-100/50 p-4 rounded-xl text-sm text-zinc-700 relative hover:border-amber-200 transition-colors"
                        >
                          <div className="flex justify-between items-start mb-1">
                            <span className="text-[10px] font-bold text-amber-300">
                              {note.date}
                            </span>
                            <button
                              onClick={(event) => {
                                event.stopPropagation();
                                noteActions.deleteNote(note.id).catch(() => {});
                              }}
                              className="p-0.5 text-zinc-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                              title="删除笔记"
                            >
                              <X size={12} />
                            </button>
                          </div>
                          <div className="mb-2 text-[10px] font-medium text-zinc-400">
                            点击即可编辑
                          </div>
                          <MarkdownContent
                            content={note.content}
                            className="space-y-2 leading-6 text-zinc-700"
                          />
                        </div>
                      ))
                    ) : (
                      <div
                        onClick={openNewNoteEditor}
                        className="border border-dashed border-zinc-200 rounded-xl p-6 text-center text-zinc-400 text-sm hover:bg-zinc-50 hover:border-zinc-300 cursor-pointer transition-all"
                      >
                        这里还没有内容，记下你的思考吧。
                      </div>
                    )}
                  </div>
                </section>
              </div>
            </div>
          </>
        )}
      </div>

      {/* F4: Chat Panel */}
      {selectedNode && (
        <>
          {/* Floating chat button */}
          <button
            onClick={() => {
              setChatOpen((v) => !v);
              if (!chatOpen) {
                // Reset messages when reopening for a different context
                setChatMessages([]);
              }
            }}
            className={`absolute bottom-8 left-8 z-20 w-12 h-12 rounded-2xl shadow-lg flex items-center justify-center transition-all ${
              chatOpen
                ? "bg-zinc-900 text-white shadow-zinc-900/20"
                : "bg-white text-zinc-600 border border-zinc-200 hover:border-zinc-400 hover:text-zinc-900"
            }`}
            title="AI 学习助手"
          >
            {chatOpen ? <X size={18} strokeWidth={1.5} /> : <MessageCircle size={18} strokeWidth={1.5} />}
          </button>

          {/* Chat panel */}
          <div
            className={`absolute bottom-24 left-8 z-20 flex min-h-0 flex-col overflow-hidden rounded-3xl border border-zinc-100 bg-white/95 shadow-2xl backdrop-blur-xl transition-all duration-300 origin-bottom-left ${
              chatOpen ? "opacity-100 scale-100 pointer-events-auto" : "opacity-0 scale-95 pointer-events-none"
            }`}
            style={{
              width: chatPanelSize.width,
              height: chatPanelSize.height,
              maxHeight: "calc(100vh - 120px)",
            }}
          >
            <button
              type="button"
              onMouseDown={handleChatResizeStart}
              className={`absolute right-3 top-3 z-10 flex h-5 w-5 cursor-nesw-resize items-center justify-center rounded-full border border-zinc-200 bg-white/90 text-zinc-400 shadow-sm transition-colors ${
                isChatResizing ? "border-teal-300 text-teal-500" : "hover:border-zinc-300 hover:text-zinc-600"
              }`}
              title="拖动调整助手窗口大小"
            >
              <span className="pointer-events-none text-[10px] leading-none">⋰</span>
            </button>
            {/* Header */}
            <div className="px-5 py-4 border-b border-zinc-50 flex items-center gap-3 flex-shrink-0 pr-11">
              <div className="w-7 h-7 rounded-xl bg-teal-50 flex items-center justify-center text-teal-600">
                <Sparkles size={13} fill="currentColor" />
              </div>
              <div>
                <p className="text-xs font-bold text-zinc-800">AI 学习助手</p>
                <p className="text-[10px] text-zinc-400 truncate max-w-[180px]">{selectedNode.name}</p>
              </div>
              <button
                type="button"
                onClick={handleSaveChatSummary}
                disabled={!chatMessages.length || isSavingChatSummary}
                className="ml-auto rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-[10px] font-medium text-teal-700 transition-colors hover:border-teal-300 hover:bg-teal-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSavingChatSummary
                  ? "保存中..."
                  : chatSummarySaved
                    ? "已保存"
                    : "总结并保存"}
              </button>
              <button
                onClick={() => setChatMessages([])}
                className="text-[10px] text-zinc-300 hover:text-zinc-500 transition-colors"
              >
                清空
              </button>
            </div>

            {/* Messages */}
            <div
              ref={chatMessagesRef}
              className="min-h-0 flex-1 overflow-y-auto px-4 py-3 space-y-3 custom-scrollbar"
            >
              {chatMessages.length === 0 && (
                <div className="text-center text-xs text-zinc-300 pt-8">
                  <MessageCircle size={24} className="mx-auto mb-2 opacity-30" />
                  <p>有什么关于“{selectedNode.name}”的问题？</p>
                </div>
              )}
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  {msg.role === "user" ? (
                    <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-zinc-900 px-3 py-2 text-xs leading-relaxed text-white">
                      {msg.content}
                    </div>
                  ) : (
                    <ChatMarkdownMessage
                      content={msg.content}
                      isPending={!msg.content}
                      sources={msg.sources || []}
                      searchStatus={msg.searchStatus || null}
                    />
                  )}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-zinc-50 px-3 py-3 flex-shrink-0">
              <button
                type="button"
                onClick={() => setChatWebSearchEnabled((prev) => !prev)}
                className={`mb-3 inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-medium transition-colors ${
                  chatWebSearchEnabled
                    ? "border-teal-300 bg-teal-50 text-teal-700"
                    : "border-zinc-200 bg-white text-zinc-500 hover:border-zinc-300 hover:text-zinc-700"
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    chatWebSearchEnabled ? "bg-teal-400" : "bg-zinc-300"
                  }`}
                />
                联网搜索
              </button>
              <div className="flex gap-2">
                <input
                  type="text"
                  className="flex-1 rounded-xl border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs outline-none transition-colors focus:border-zinc-300"
                  placeholder="问一个问题..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleChatSend()}
                  disabled={chatLoading}
                />
                <button
                  onClick={handleChatSend}
                  disabled={!chatInput.trim() || chatLoading}
                  className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-zinc-900 text-white transition-colors hover:bg-zinc-700 disabled:opacity-30"
                >
                  {chatLoading ? <Loader size={12} className="animate-spin" /> : <Send size={12} />}
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      <MasteryQuizModal
        quiz={masteryQuiz}
        onClose={() => setMasteryQuiz(null)}
        onPassed={handleMasteryQuizPassed}
      />

      {/* Goal Clarification Modal */}
      <Modal
        isOpen={showGoalClarification}
        onClose={() => setShowGoalClarification(false)}
        title="修改学习目标"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => setShowGoalClarification(false)}
            >
              取消
            </Button>
            {!clarifyResult ? (
              <Button
                onClick={handleClarifyGoal}
                disabled={isClarifying || !newGoalInput.trim()}
              >
                {isClarifying ? "分析中..." : "分析变更"}
              </Button>
            ) : (
              <Button onClick={handleApplyClarify}>
                {clarifyResult.isLargeChange ? "新建计划" : "应用修改"}
              </Button>
            )}
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <p className="text-xs text-zinc-400 mb-2">当前目标</p>
            <p className="text-sm text-zinc-600 bg-zinc-50 px-3 py-2 rounded-lg">
              {plan?.title}
            </p>
          </div>
          <div>
            <p className="text-xs text-zinc-400 mb-2">新目标</p>
            <textarea
              className="w-full h-24 p-3 text-sm border border-zinc-200 rounded-lg resize-none outline-none focus:border-zinc-400 transition-colors"
              placeholder="输入修改后的学习目标..."
              value={newGoalInput}
              onChange={(e) => {
                setNewGoalInput(e.target.value);
                setClarifyResult(null);
              }}
            />
          </div>
          {clarifyResult && (
            <div
              className={`p-4 rounded-xl border ${clarifyResult.isLargeChange ? "bg-amber-50 border-amber-200" : "bg-teal-50 border-teal-200"}`}
            >
              <p className="text-sm font-medium mb-1">
                {clarifyResult.isLargeChange
                  ? "目标变化较大，建议新建计划"
                  : "小幅调整，将更新现有图谱"}
              </p>
              <p className="text-xs text-zinc-500">{clarifyResult.reason}</p>
            </div>
          )}
        </div>
      </Modal>

      <Modal
        isOpen={showPlanSettings}
        onClose={() => setShowPlanSettings(false)}
        title="学习计划设置"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowPlanSettings(false)}>
              取消
            </Button>
            <Button onClick={handleSavePlanSettings} disabled={isUpdatingPlanSettings}>
              {isUpdatingPlanSettings ? "保存中..." : "保存设置"}
            </Button>
          </>
        }
      >
        <div className="space-y-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="space-y-2">
              <span className="text-xs font-medium text-zinc-500">开始日期</span>
              <input
                type="date"
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none transition-colors focus:border-zinc-400"
                value={planSettings.startDate}
                onChange={(e) => handlePlanSettingChange("startDate", e.target.value)}
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-medium text-zinc-500">目标完成日期</span>
              <input
                type="date"
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none transition-colors focus:border-zinc-400"
                value={planSettings.targetEndDate}
                onChange={(e) =>
                  handlePlanSettingChange("targetEndDate", e.target.value)
                }
              />
            </label>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[minmax(0,1fr)_140px]">
            <label className="space-y-2">
              <span className="text-xs font-medium text-zinc-500">学习频率</span>
              <select
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none transition-colors focus:border-zinc-400"
                value={planSettings.studyFrequency}
                onChange={(e) =>
                  handlePlanSettingChange("studyFrequency", e.target.value)
                }
              >
                {PLAN_FREQUENCY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2">
              <span className="text-xs font-medium text-zinc-500">每周次数</span>
              <input
                type="number"
                min="1"
                max="7"
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none transition-colors focus:border-zinc-400"
                value={planSettings.studyDaysPerWeek}
                onChange={(e) =>
                  handlePlanSettingChange("studyDaysPerWeek", e.target.value)
                }
              />
            </label>
          </div>

          <div className="rounded-2xl border border-zinc-200 bg-zinc-50/70 p-4">
            <label className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-zinc-800">学习提醒</p>
                <p className="text-xs text-zinc-500">先用站内节奏管理，后续再接系统提醒。</p>
              </div>
              <button
                type="button"
                onClick={() =>
                  handlePlanSettingChange(
                    "reminderEnabled",
                    !planSettings.reminderEnabled,
                  )
                }
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors ${
                  planSettings.reminderEnabled ? "bg-teal-500" : "bg-zinc-300"
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                    planSettings.reminderEnabled
                      ? "translate-x-6"
                      : "translate-x-1"
                  }`}
                />
              </button>
            </label>

            {planSettings.reminderEnabled ? (
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <label className="space-y-2">
                  <span className="text-xs font-medium text-zinc-500">提醒时间</span>
                  <input
                    type="time"
                    className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none transition-colors focus:border-zinc-400"
                    value={planSettings.reminderTime}
                    onChange={(e) =>
                      handlePlanSettingChange("reminderTime", e.target.value)
                    }
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium text-zinc-500">时区</span>
                  <input
                    type="text"
                    className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none transition-colors focus:border-zinc-400"
                    value={planSettings.reminderTimezone}
                    onChange={(e) =>
                      handlePlanSettingChange("reminderTimezone", e.target.value)
                    }
                  />
                </label>
              </div>
            ) : null}
          </div>
        </div>
      </Modal>

      {/* Note Editor Modal */}
      <Modal
        isOpen={showNoteEditor}
        onClose={() => {
          setShowNoteEditor(false);
          setEditingNoteId(null);
          setNoteContent("");
        }}
        title={editingNoteId ? "编辑笔记" : "新笔记"}
        footer={<Button onClick={handleSaveNote}>{editingNoteId ? "保存修改" : "保存笔记"}</Button>}
      >
        <textarea
          className="w-full h-64 p-4 bg-zinc-50 border border-zinc-100 rounded-xl outline-none resize-none focus:bg-white focus:border-zinc-300 transition-colors font-mono text-sm leading-relaxed"
          placeholder="支持 Markdown 格式..."
          value={noteContent}
          onChange={(e) => setNoteContent(e.target.value)}
          autoFocus
        />
      </Modal>

      <Modal
        isOpen={showLeaveConfirm}
        onClose={() => setShowLeaveConfirm(false)}
        title="保存学习计划？"
        footer={
          <div className="flex gap-3 w-full">
            <Button
              variant="ghost"
              className="flex-1"
              onClick={() => {
                setShowLeaveConfirm(false);
                navigate("/");
              }}
            >
              不保存
            </Button>
            <Button
              variant="secondary"
              className="flex-1"
              onClick={() => setShowLeaveConfirm(false)}
            >
              取消
            </Button>
            <Button
              className="flex-1"
              onClick={async () => {
                await handleSavePlan();
                setShowLeaveConfirm(false);
                navigate("/");
              }}
            >
              保存
            </Button>
          </div>
        }
      >
        <p className="text-sm text-zinc-500">保存后可在首页继续学习。</p>
      </Modal>
    </div>
  );
};

export default GraphPage;
