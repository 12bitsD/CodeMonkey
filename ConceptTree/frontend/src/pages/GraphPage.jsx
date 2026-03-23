import React, { useState, useRef, useEffect } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  Share2,
  Edit3,
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
} from "lucide-react";
import { Button, Modal } from "../components/ui";
import { InfoSection } from "../components/common";
import { MasteryChecklist } from "../components/node/MasteryChecklist";
import { ResourceList } from "../components/node/ResourceList";
import { useGraphInteraction } from "../hooks/useGraphInteraction";
import { useAppContext } from "../contexts/AppContext";
import { useToast } from "../contexts/ToastContext";
import { graphApi, aiApi, plansApi } from "../services/api";
import { toggleNodeStatus, isAllComplete } from "../utils/graphUtils";

const GraphPage = () => {
  const { planId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const containerRef = useRef(null);
  const draggingPosRef = useRef({ id: null, x: 0, y: 0 });
  const { plans, allNotes, actions } = useAppContext();
  const toast = useToast();

  const plan = plans.find((p) => p.id === planId);
  const [loading, setLoading] = useState(true);
  const [isDirty, setIsDirty] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const [aiRecommendation, setAiRecommendation] = useState(null);

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
    resetView,
    zoomIn,
    zoomOut,
  } = useGraphInteraction([], [], aiRecommendation);

  useEffect(() => {
    const loadGraph = async () => {
      if (!planId) return;
      setLoading(true);
      try {
        const data = await graphApi.get(planId);
        if (data && data.nodes) {
          setNodes(data.nodes);
          setEdges(data.edges || []);
        }
      } catch (err) {
        console.error("Failed to load graph", err);
      } finally {
        setLoading(false);
      }
    };

    loadGraph();
  }, [planId, setNodes, setEdges]);

  useEffect(() => {
    const nodeId = searchParams.get("node");
    if (nodeId && !loading && nodes.length > 0) {
      setSelectedNodeId(nodeId);
    }
  }, [searchParams, loading, nodes.length, setSelectedNodeId]);

  useEffect(() => {
    if (!planId || loading) return;
    aiApi
      .recommendNext(planId)
      .then((data) => {
        if (data?.recommended_node_id) {
          setAiRecommendation(data);
        }
      })
      .catch(() => {});
  }, [planId, loading]);

  const [showGoalClarification, setShowGoalClarification] = useState(false);
  const [newGoalInput, setNewGoalInput] = useState("");
  const [clarifyResult, setClarifyResult] = useState(null);
  const [isClarifying, setIsClarifying] = useState(false);
  const [showNoteEditor, setShowNoteEditor] = useState(false);
  const [noteContent, setNoteContent] = useState("");

  const nodeNotes = allNotes.filter(
    (n) => n.planId === planId && n.nodeId === selectedNodeId,
  );

  const learnedCount = nodes.filter((n) => n.status === "learned").length;
  const totalCount = nodes.filter((n) => n.status !== "skipped").length;

  const handleSaveNote = async () => {
    if (noteContent.trim()) {
      await actions.addNote(planId, selectedNodeId, noteContent);
    }
    setNoteContent("");
    setShowNoteEditor(false);
  };

  const handleCopyPrompt = (prompt) => {
    navigator.clipboard.writeText(prompt);
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
      }
      toast.success("目标已更新");
    } catch (err) {
      toast.error("应用修改失败，请重试");
    }
  };

  const handleNodeStatusChange = async (nodeId, newStatus) => {
    setNodeStatus(nodeId, newStatus);
    setIsDirty(true);
    actions.updateNodeStatusInPlan(planId, nodeId, newStatus);
    try {
      await graphApi.updateNodeStatus(planId, nodeId, newStatus);
    } catch (err) {
      console.error("Failed to save node status", err);
    }
  };

  const handleDoubleClickNode = (e, nodeId, currentStatus) => {
    e.stopPropagation();
    handleNodeStatusChange(nodeId, toggleNodeStatus(currentStatus));
  };

  const handleSavePlan = async () => {
    if (!planId || isSaving) return;
    setIsSaving(true);
    try {
      await plansApi.update(planId, { title: plan?.title });
      setSavedAt(new Date());
      setIsDirty(false);
      toast.success("计划已保存");
    } catch {
      toast.error("保存失败，请重试");
    } finally {
      setIsSaving(false);
    }
  };

  const handleNavigateBack = () => {
    if (isDirty) {
      setShowLeaveConfirm(true);
    } else {
      navigate("/");
    }
  };

  const handleContainerMouseMove = (e) => {
    handleMouseMove(e, containerRef);
    if (draggingNodeId && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      draggingPosRef.current = {
        id: draggingNodeId,
        x: (e.clientX - rect.left - position.x) / scale,
        y: (e.clientY - rect.top - position.y) / scale,
      };
    }
  };

  const handleContainerMouseUp = () => {
    const { id, x, y } = draggingPosRef.current;
    handleMouseUp();
    if (id) {
      graphApi.updateNodePosition(planId, id, x, y).catch((err) => {
        console.error("Failed to save node position", err);
      });
      draggingPosRef.current = { id: null, x: 0, y: 0 };
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
                {plan?.title || "加载中..."}
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
            </div>
          </div>

          <div className="bg-white/90 backdrop-blur-md p-2 rounded-2xl shadow-sm border border-zinc-200/50 pointer-events-auto flex gap-1 items-center">
            {savedAt && !isDirty ? (
              <span className="text-[10px] text-zinc-400 px-2">
                已保存{" "}
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
              title="Share"
            >
              <Share2 size={18} strokeWidth={1.5} />
            </button>
            <button
              className="p-2 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-50 rounded-xl transition-all"
              title="Edit Goal"
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
        className="flex-1 cursor-grab active:cursor-grabbing"
        ref={containerRef}
        onMouseDown={(e) => handleMouseDown(e, containerRef)}
        onMouseMove={handleContainerMouseMove}
        onMouseUp={handleContainerMouseUp}
        onMouseLeave={handleContainerMouseUp}
        onWheel={handleWheel}
      >
        <div
          className="absolute inset-0 opacity-[0.03]"
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
            {edges.map((edge, i) => {
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
                    stroke={isTraversed ? "#0D9488" : "#E4E4E7"}
                    strokeWidth={isTraversed ? 1.5 : 1}
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
            return (
              <div
                key={node.id}
                className={`absolute transform -translate-x-1/2 -translate-y-1/2 transition-all duration-300 flex items-center justify-center cursor-pointer
                  ${scale < 0.6 ? "w-4 h-4 rounded-full" : "w-auto h-auto px-6 py-3 rounded-full"}
                  ${isSelected ? "scale-110 shadow-[0_10px_40px_rgba(0,0,0,0.1)] z-10" : "shadow-[0_2px_10px_rgba(0,0,0,0.03)] hover:shadow-lg z-0"}
                  ${isLearned ? "bg-zinc-900 text-white border border-zinc-800" : "bg-white text-zinc-600 border border-zinc-200 hover:border-zinc-300"}
                  ${node.isTarget && !isLearned ? "ring-2 ring-teal-500/20 border-teal-500 text-teal-700" : ""}
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
                  isLearned ? (
                    <div className="w-2 h-2 bg-emerald-400 rounded-full" />
                  ) : (
                    <div className="w-2 h-2 bg-zinc-300 rounded-full" />
                  )
                ) : (
                  <div className="flex items-center gap-3">
                    {isLearned ? (
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
                        className="text-zinc-300"
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
              <span className="text-sm">💡</span>
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
          onClick={resetView}
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
                    </h4>
                    <ul className="space-y-3">
                      {selectedNode.what.map((item, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-3 text-sm text-zinc-600 group"
                        >
                          <div className="w-1.5 h-1.5 rounded-full bg-zinc-200 mt-2 group-hover:bg-teal-500 transition-colors" />
                          <span className="leading-relaxed">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                {selectedNode.mastery?.length > 0 && (
                  <MasteryChecklist items={selectedNode.mastery} />
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

                {selectedNode.resources?.length > 0 && (
                  <ResourceList resources={selectedNode.resources} />
                )}

                <button
                  onClick={() =>
                    window.open(
                      `https://www.google.com/search?q=${encodeURIComponent(selectedNode.name + " 学习教程")}`,
                      "_blank",
                    )
                  }
                  className="w-full py-2.5 text-xs text-zinc-400 hover:text-zinc-600 border border-dashed border-zinc-200 rounded-xl hover:border-zinc-300 transition-colors"
                >
                  搜索更多资源 ↗
                </button>

                {/* Notes */}
                <section>
                  <div className="flex justify-between items-center mb-4">
                    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
                      <FileText size={14} /> 笔记
                    </h4>
                    <button
                      onClick={() => setShowNoteEditor(true)}
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
                          className="group bg-amber-50/50 border border-amber-100/50 p-4 rounded-xl text-sm text-zinc-700 relative hover:border-amber-200 transition-colors"
                        >
                          <div className="flex justify-between items-start mb-1">
                            <span className="text-[10px] font-bold text-amber-300">
                              {note.date}
                            </span>
                            <button
                              onClick={() => actions.deleteNote(note.id)}
                              className="p-0.5 text-zinc-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                              title="删除笔记"
                            >
                              <X size={12} />
                            </button>
                          </div>
                          <p className="leading-relaxed">{note.content}</p>
                        </div>
                      ))
                    ) : (
                      <div
                        onClick={() => setShowNoteEditor(true)}
                        className="border border-dashed border-zinc-200 rounded-xl p-6 text-center text-zinc-400 text-sm hover:bg-zinc-50 hover:border-zinc-300 cursor-pointer transition-all"
                      >
                        空空如也。记录下你的思考吧。
                      </div>
                    )}
                  </div>
                </section>
              </div>
            </div>
          </>
        )}
      </div>

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
                  ? "🔄 目标变化较大，建议新建计划"
                  : "✏️ 小幅调整，将更新现有图谱"}
              </p>
              <p className="text-xs text-zinc-500">{clarifyResult.reason}</p>
            </div>
          )}
        </div>
      </Modal>

      {/* Note Editor Modal */}
      <Modal
        isOpen={showNoteEditor}
        onClose={() => setShowNoteEditor(false)}
        title="新笔记"
        footer={<Button onClick={handleSaveNote}>保存笔记</Button>}
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
        <p className="text-sm text-zinc-500">保存后可在首页继续学习</p>
      </Modal>
    </div>
  );
};

export default GraphPage;
