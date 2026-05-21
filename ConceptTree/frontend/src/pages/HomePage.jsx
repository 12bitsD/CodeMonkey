import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Archive,
  Bell,
  BrainCircuit,
  CalendarDays,
  Edit3,
  LogOut,
  MoreVertical,
  Pause,
  Play,
  Sparkles,
  Target,
  User,
  ChevronRight,
} from "lucide-react";
import { Button, Modal } from "../components/ui";
import GoalAnalysisLoader from "../components/loaders/GoalAnalysisLoader";
import GraphGenerationLoader from "../components/loaders/GraphGenerationLoader";
import { LOADING_TEXTS } from "../constants";
import { useAuth } from "../contexts/AuthContext";
import { usePlanContext } from "../contexts/PlanContext";
import { useToast } from "../contexts/ToastContext";
import { aiApi, plansApi } from "../services/api";
import { calculateLayout } from "../utils/layoutEngine";
import { getPlanReminder, getTopPlanReminder } from "../utils/planReminders";

const TODAY_RECOMMENDATION_CACHE_KEY = "concept_tree_today_recommendation";

const getTodayCacheDate = () => {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const buildRecommendationCacheKey = (plan, dateKey = getTodayCacheDate()) => {
  if (!plan?.id) return null;
  return [
    dateKey,
    plan.id,
    plan.progress ?? 0,
    plan.total ?? 0,
    plan.status || "active",
    plan.targetEndDate || "",
  ].join("|");
};

const readTodayRecommendationCache = (cacheKey) => {
  if (!cacheKey || typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(TODAY_RECOMMENDATION_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.cacheKey === cacheKey ? parsed.data || null : null;
  } catch {
    return null;
  }
};

const writeTodayRecommendationCache = (cacheKey, data) => {
  if (!cacheKey || !data || typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      TODAY_RECOMMENDATION_CACHE_KEY,
      JSON.stringify({ cacheKey, data, savedAt: new Date().toISOString() }),
    );
  } catch {
    // localStorage can be unavailable in private or restricted contexts.
  }
};

const PURPOSE_OPTIONS = [
  { id: "explore", label: "了解领域", description: "更轻的认知入门图谱" },
  { id: "apply", label: "项目实用", description: "围绕可上手和可实践展开" },
  { id: "master", label: "系统掌握", description: "更完整、更深入的学习路径" },
];

const getFrequencyLabel = (frequency, daysPerWeek) => {
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

const getPlanStatusLabel = (plan) => {
  if (plan.status === "paused") return "已暂停";
  if (plan.archivedReason === "completed") return "已完成";
  if (plan.status === "archived") return "已归档";
  return "进行中";
};

const formatPlanDate = (value) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("zh-CN", {
    month: "numeric",
    day: "numeric",
  });
};

const getReminderTone = (level) => {
  switch (level) {
    case "deadline":
      return "bg-amber-100 text-amber-800 border-amber-200";
    case "overdue":
      return "bg-rose-100 text-rose-800 border-rose-200";
    case "due":
      return "bg-teal-100 text-teal-800 border-teal-200";
    case "paused":
      return "bg-zinc-200 text-zinc-700 border-zinc-300";
    default:
      return "bg-white/10 text-zinc-200 border-white/10";
  }
};

const HomePage = () => {
  const navigate = useNavigate();
  const { userProfile, plans, actions } = usePlanContext();
  const { isAuthenticated, logout } = useAuth();
  const toast = useToast();

  const [inputText, setInputText] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [streamProgress, setStreamProgress] = useState(null);
  const [generationPhase, setGenerationPhase] = useState(1);
  const [skeletonNodeCount, setSkeletonNodeCount] = useState(0);
  const [readyNodeCount, setReadyNodeCount] = useState(0);
  const [totalNodeCount, setTotalNodeCount] = useState(0);
  const [currentlyProcessing, setCurrentlyProcessing] = useState("");
  const [pendingNodeIds, setPendingNodeIds] = useState(new Set());
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [parsedGoal, setParsedGoal] = useState(null);
  const [learningPurpose, setLearningPurpose] = useState("apply");
  const [activeMenuPlanId, setActiveMenuPlanId] = useState(null);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [planToRename, setPlanToRename] = useState(null);
  const [newName, setNewName] = useState("");
  const [todayRecommendation, setTodayRecommendation] = useState(null);
  const [isLoadingRecommendation, setIsLoadingRecommendation] = useState(false);
  const isLoadingScene = isAnalyzing || isGenerating;
  const [deadlinePlan, setDeadlinePlan] = useState(null);
  const [deadlineInput, setDeadlineInput] = useState("");
  const [isSavingDeadline, setIsSavingDeadline] = useState(false);

  const currentPlans = useMemo(
    () => plans.filter((plan) => plan.status === "active" || plan.status === "paused"),
    [plans],
  );

  const topReminder = useMemo(() => getTopPlanReminder(currentPlans), [currentPlans]);
  const todayPlan = topReminder?.plan || currentPlans[0] || null;
  const todayReminder = topReminder?.reminder || (todayPlan ? getPlanReminder(todayPlan) : null);
  const todayPlanId = todayPlan?.id || null;
  const todayPlanStatus = todayPlan?.status || null;
  const todayRecommendationCacheKey = useMemo(
    () => buildRecommendationCacheKey(todayPlan),
    [todayPlan],
  );

  useEffect(() => {
    let cancelled = false;

    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 15000);

    const loadRecommendation = async () => {
      if (!isAuthenticated || !todayPlanId || todayPlanStatus !== "active") {
        setTodayRecommendation(null);
        clearTimeout(timeoutId);
        return;
      }

      const cached = readTodayRecommendationCache(todayRecommendationCacheKey);
      if (cached) {
        setTodayRecommendation(cached);
        setIsLoadingRecommendation(false);
        clearTimeout(timeoutId);
        return;
      }

      setIsLoadingRecommendation(true);
      try {
        const result = await aiApi.recommendNext(todayPlanId, {
          signal: abortController.signal,
        });
        if (!cancelled) {
          setTodayRecommendation(result || null);
          if (result?.recommended_node_id) {
            writeTodayRecommendationCache(todayRecommendationCacheKey, result);
          }
        }
      } catch (error) {
        if (!cancelled && error?.name !== "AbortError") {
          setTodayRecommendation(null);
        }
      } finally {
        clearTimeout(timeoutId);
        if (!cancelled) {
          setIsLoadingRecommendation(false);
        }
      }
    };

    loadRecommendation();

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
      abortController.abort();
    };
  }, [isAuthenticated, todayPlanId, todayPlanStatus, todayRecommendationCacheKey]);

  const openDeadlineModal = (plan) => {
    if (!plan) return;
    setDeadlinePlan(plan);
    setDeadlineInput(plan.targetEndDate ? String(plan.targetEndDate).slice(0, 10) : "");
  };

  const saveDeadline = async () => {
    if (!deadlinePlan) return;
    const planId = deadlinePlan.id;
    const nextTargetEndDate = deadlineInput || null;
    const previousPlans = plans;

    actions.setPlans((prev) =>
      prev.map((plan) =>
        plan.id === planId
          ? {
              ...plan,
              targetEndDate: nextTargetEndDate,
              lastAccess: plan.lastAccess || new Date().toISOString(),
            }
          : plan,
      ),
    );
    setDeadlinePlan(null);
    setDeadlineInput("");
    setIsSavingDeadline(false);

    try {
      const updated = await plansApi.update(planId, {
        targetEndDate: nextTargetEndDate,
      });
      actions.setPlans((prev) =>
        prev.map((plan) => (plan.id === planId ? { ...plan, ...updated } : plan)),
      );
      toast.success(nextTargetEndDate ? "截止日期已更新" : "截止日期已清除");
    } catch (error) {
      actions.setPlans(previousPlans);
      toast.error("截止日期保存失败，已恢复原设置");
    }
  };

  const handleStartAnalysis = async () => {
    if (!inputText.trim()) return;
    if (!isAuthenticated) {
      toast.info('请先登录后再使用 AI 生成功能');
      navigate('/auth?redirect=%2F');
      return;
    }
    setIsAnalyzing(true);
    setAnalysisStep(0);
    let step = 0;
    const interval = setInterval(() => {
      step += 1;
      setAnalysisStep(step);
    }, 900);

    try {
      const result = await aiApi.parseGoal(inputText, userProfile);
      setParsedGoal(result);
      setShowConfirmModal(true);
    } catch (error) {
      toast.error("解析目标失败，请稍后重试");
    } finally {
      clearInterval(interval);
      setIsAnalyzing(false);
    }
  };

  const handleConfirmGeneration = async () => {
    const confirmedInterpretation = parsedGoal?.interpretation?.trim() || inputText;
    setShowConfirmModal(false);
    setIsGenerating(true);
    setLoadingStep(0);
    setStreamProgress(null);
    setGenerationPhase(1);
    setSkeletonNodeCount(0);
    setReadyNodeCount(0);
    setTotalNodeCount(0);
    setCurrentlyProcessing("");
    setPendingNodeIds(new Set());

    let step = 0;
    const interval = setInterval(() => {
      step += 1;
      setLoadingStep(step);
      if (step >= LOADING_TEXTS.length) {
        clearInterval(interval);
      }
    }, 800);

    try {
      const skeletonRef = { nodes: [], edges: [], targetNodeId: "", positions: {} };
      const nodeContentsRef = {};
      let integrationRevisions = [];

      await aiApi.generateV2(
        inputText,
        confirmedInterpretation,
        learningPurpose,
        userProfile,
        {
          onSkeleton: (data) => {
            skeletonRef.nodes = data.nodes || [];
            skeletonRef.edges = data.edges || [];
            skeletonRef.targetNodeId = data.targetNodeId || "";
            skeletonRef.positions = calculateLayout(
              skeletonRef.nodes,
              skeletonRef.edges,
              skeletonRef.targetNodeId,
            );

            const pendingIds = skeletonRef.nodes.map((node) => node.id);
            setPendingNodeIds(new Set(pendingIds));
            setSkeletonNodeCount(skeletonRef.nodes.length);
            setTotalNodeCount(data.total_nodes || skeletonRef.nodes.length);
            setReadyNodeCount(0);
            setGenerationPhase(2);
            setCurrentlyProcessing(skeletonRef.nodes[0]?.name || "");
            setStreamProgress({
              received: 0,
              total: data.total_nodes || skeletonRef.nodes.length,
            });
          },
          onNodeReady: (content) => {
            nodeContentsRef[content.node_id] = content;
            setPendingNodeIds((prev) => {
              const next = new Set(prev);
              next.delete(content.node_id);
              const nextPendingId = [...next][0];
              const nextNode = skeletonRef.nodes.find((node) => node.id === nextPendingId);
              setCurrentlyProcessing(nextNode?.name || "");
              return next;
            });
            setReadyNodeCount((prev) => {
              const next = prev + 1;
              setStreamProgress({
                received: next,
                total: skeletonRef.nodes.length,
              });
              return next;
            });
          },
          onIntegrationDone: (data) => {
            setGenerationPhase(3);
            integrationRevisions = data?.revised_nodes || [];
          },
          onError: (err) => {
            console.error("[generateV2] fatal error:", err);
          },
        },
      );

      const revisionsByNodeId = new Map(
        integrationRevisions.map((revision) => [revision.node_id, revision.what]),
      );
      const graphResult = {
        interpretation: confirmedInterpretation,
        targetNodeId: skeletonRef.targetNodeId,
        edges: skeletonRef.edges,
        nodes: skeletonRef.nodes.map((node) => {
          const content = nodeContentsRef[node.id] || {};
          const revisedWhat = revisionsByNodeId.get(node.id);
          const position = skeletonRef.positions[node.id] || { x: 0, y: 0 };
          return {
            id: node.id,
            name: node.name,
            domain: node.domain || null,
            status: "unlearned",
            x: position.x,
            y: position.y,
            isTarget: node.id === skeletonRef.targetNodeId,
            why: content.why || "",
            what: revisedWhat || content.what || [],
            mastery: content.mastery || [],
            prompt: content.prompt || "",
            resources: content.resources || [],
          };
        }),
      };

      const newPlan = await actions.createPlan(inputText, graphResult, learningPurpose);

      clearInterval(interval);
      setTimeout(() => {
        setIsGenerating(false);
        setStreamProgress(null);
        setPendingNodeIds(new Set());
        setCurrentlyProcessing("");
        navigate(`/graph/${newPlan.id}`);
        setInputText("");
      }, 500);
    } catch (error) {
      toast.error("生成图谱失败，请稍后重试");
      clearInterval(interval);
      setIsGenerating(false);
      setStreamProgress(null);
      setPendingNodeIds(new Set());
      setCurrentlyProcessing("");
    }
  };

  const handleArchive = async (id) => {
    await actions.archivePlan(id, "manual");
    setActiveMenuPlanId(null);
  };

  const handlePauseToggle = async (plan) => {
    if (plan.status === "paused") {
      await actions.resumePlan(plan.id);
    } else {
      await actions.pausePlan(plan.id);
    }
    setActiveMenuPlanId(null);
  };

  const openRenameModal = (plan) => {
    setPlanToRename(plan);
    setNewName(plan.title);
    setShowRenameModal(true);
    setActiveMenuPlanId(null);
  };

  const saveNewName = async () => {
    if (!planToRename || !newName.trim()) return;
    await actions.updatePlan(planToRename.id, { title: newName.trim() });
    setShowRenameModal(false);
  };

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div
      className="relative mx-auto flex min-h-screen max-w-screen-xl flex-col px-6 py-10 md:px-12"
      onClick={() => setActiveMenuPlanId(null)}
    >
      <header className="mb-20 flex items-center justify-between">
        <div
          className="group flex cursor-pointer items-center gap-3"
          onClick={() => navigate("/")}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-900 text-white shadow-lg shadow-zinc-200 transition-transform group-hover:rotate-3 group-hover:scale-105">
            <BrainCircuit size={20} strokeWidth={1.5} />
          </div>
          <span className="text-lg font-semibold tracking-tight text-zinc-900">
            PathFinder
          </span>
        </div>

        {!isAuthenticated ? (
          <button
            onClick={() => navigate("/auth")}
            className="rounded-full bg-zinc-900 px-6 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:-translate-y-0.5 hover:bg-zinc-800 hover:shadow-md active:translate-y-0"
          >
            登录 / 注册
          </button>
        ) : (
          <div className="flex items-center gap-2 rounded-full border border-zinc-100 bg-white p-1.5 shadow-sm">
            <button
              onClick={() => navigate("/my-learning")}
              className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-zinc-600 transition-all duration-200 hover:bg-zinc-50 hover:text-zinc-900"
            >
              <User size={16} strokeWidth={2} />
              我的学习
            </button>
            <div className="h-4 w-px bg-zinc-200" />
            <button
              onClick={handleLogout}
              className="rounded-full p-2 text-zinc-400 transition-all duration-200 hover:bg-red-50 hover:text-red-600"
              title="退出登录"
            >
              <LogOut size={16} strokeWidth={2} />
            </button>
          </div>
        )}
      </header>

      <section className="mx-auto mb-20 flex w-full max-w-3xl flex-1 flex-col justify-center">
        <div className="mb-12 space-y-4 text-center">
          <h1 className="text-4xl font-light leading-tight tracking-tight text-zinc-900 md:text-5xl">
            今天想<span className="font-medium">掌握</span>什么？
          </h1>
          <p className="text-lg font-light text-zinc-400">
            AI 驱动的学习路径规划器，会根据你的背景和目标生成更适合的图谱。
          </p>
        </div>

        {isLoadingScene ? (
          <div className="relative min-h-[430px] overflow-hidden rounded-3xl border border-zinc-100 bg-white shadow-[0_8px_40px_rgba(0,0,0,0.04)]">
            {isAnalyzing ? <GoalAnalysisLoader step={analysisStep} /> : null}
            {isGenerating ? (
              <GraphGenerationLoader
                phase={generationPhase}
                skeletonNodeCount={skeletonNodeCount}
                readyCount={readyNodeCount}
                totalCount={totalNodeCount}
                currentlyProcessing={
                  currentlyProcessing || (pendingNodeIds.size > 0 ? "排队中的节点" : "")
                }
                loadingStep={loadingStep}
                streamProgress={streamProgress}
              />
            ) : null}
          </div>
        ) : (
          <div className="group relative overflow-hidden rounded-3xl border border-zinc-100 bg-white p-2 shadow-[0_8px_40px_rgba(0,0,0,0.04)] transition-all duration-300 focus-within:border-zinc-200 focus-within:shadow-[0_12px_50px_rgba(0,0,0,0.06)]">
          <textarea
            className="h-40 w-full resize-none bg-transparent p-6 text-xl font-light leading-relaxed text-zinc-700 outline-none placeholder:text-zinc-300"
            placeholder="例如：我想理解反向传播在神经网络训练中的作用，我有 Python 基础但数学一般..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isAnalyzing || isGenerating}
          />

          <div className="flex items-end justify-between px-6 pb-6">
            <div className="flex max-w-[60%] items-center gap-3 overflow-hidden">
              {userProfile?.abilities?.slice(0, 2).map((tag) => (
                <span
                  key={tag}
                  className="whitespace-nowrap rounded-full border border-teal-100/50 bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-700"
                >
                  {tag}
                </span>
              ))}
            </div>
            <Button
              onClick={handleStartAnalysis}
              disabled={!inputText.trim() || isAnalyzing || isGenerating}
              size="md"
              icon={Sparkles}
            >
              {isAnalyzing ? "分析中..." : "生成图谱"}
            </Button>
          </div>
          </div>
        )}

        {!inputText && !isLoadingScene ? (
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            {[
              "理解反向传播算法",
              "Python 数据分析入门",
              "Transformer 架构详解",
            ].map((text) => (
              <button
                key={text}
                onClick={() => setInputText(text)}
                className="rounded-full border border-zinc-200 bg-white px-5 py-2.5 text-sm text-zinc-500 transition-all duration-200 hover:border-zinc-400 hover:text-zinc-900 hover:shadow-sm"
              >
                {text}
              </button>
            ))}
          </div>
        ) : null}
      </section>

      {todayPlan && todayReminder ? (
        <section className="mb-8 rounded-[2rem] border border-zinc-200 bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900 p-8 text-white shadow-[0_10px_40px_rgba(24,24,27,0.18)]">
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div className="min-w-0 flex-1 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-zinc-400">
                今日提醒
              </p>
              <h2 className="max-w-3xl text-2xl font-semibold leading-snug text-white md:text-[26px]">
                {todayReminder.headline}
              </h2>
              <p className="max-w-2xl text-sm leading-6 text-zinc-300">
                {todayReminder.detail}
              </p>
              <div className="flex flex-wrap items-center gap-2 text-[11px] font-medium text-zinc-300">
                <span
                  className={`inline-flex h-6 items-center rounded-full border px-3 ${getReminderTone(
                    todayReminder.level,
                  )}`}
                >
                  {getPlanStatusLabel(todayPlan)}
                </span>
                <span className="inline-flex h-6 items-center gap-1 rounded-full bg-white/10 px-3">
                  <CalendarDays size={12} />
                  {getFrequencyLabel(
                    todayPlan.studyFrequency,
                    todayPlan.studyDaysPerWeek,
                  )}
                </span>
                {todayPlan.reminderEnabled ? (
                  <span className="inline-flex h-6 items-center gap-1 rounded-full bg-white/10 px-3">
                    <Bell size={12} />
                    {todayPlan.reminderTime || "提醒已开启"}
                  </span>
                ) : null}
                {todayPlan.targetEndDate ? (
                  <span className="inline-flex h-6 items-center gap-1 rounded-full bg-white/10 px-3">
                    <Target size={12} />
                    截止 {formatPlanDate(todayPlan.targetEndDate)}
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => openDeadlineModal(todayPlan)}
                    className="inline-flex h-6 items-center gap-1 rounded-full bg-white/10 px-3 transition-colors hover:bg-white/15 hover:text-white"
                  >
                    <Target size={12} />
                    设置截止日期
                  </button>
                )}
              </div>
              {todayRecommendation?.recommended_node_id ? (
                <div className="max-w-5xl rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400">
                    {todayRecommendation.recommendation_source === "local"
                      ? "本地规则推荐节点"
                      : "AI 推荐节点"}
                  </p>
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold leading-6 text-white">
                        AI 推荐你先推进下一个关键节点
                      </p>
                      <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-300">
                        {todayRecommendation.reason || "这是当前最适合推进的下一步。"}
                      </p>
                      {todayRecommendation.recommendation_source === "local" ? (
                        <p className="mt-1 text-xs leading-5 text-zinc-500">
                          AI 暂不可用，已用本地依赖和截止日期规则生成推荐。
                        </p>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/graph/${todayPlan.id}?node=${todayRecommendation.recommended_node_id}`,
                        )
                      }
                      className="inline-flex h-11 w-full shrink-0 items-center justify-center rounded-full bg-white px-5 text-sm font-medium leading-none text-zinc-900 transition-colors hover:bg-zinc-100 md:w-auto"
                    >
                      去学习
                    </button>
                  </div>
                </div>
              ) : isLoadingRecommendation ? (
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-zinc-300">
                  正在生成今日推荐节点...
                </div>
              ) : null}
            </div>
            <div className="space-y-3 text-sm text-zinc-300 md:text-right">
              <p>
                当前进度{" "}
                <span className="font-semibold text-white">
                  {todayPlan.progress}/{todayPlan.total || 0}
                </span>
              </p>
              <p>
                {todayReminder.lastStudyDaysAgo === null
                  ? "还没有开始过这条计划"
                  : `距离上次学习 ${todayReminder.lastStudyDaysAgo} 天`}
              </p>
              <Button onClick={() => navigate(`/graph/${todayPlan.id}`)} size="sm">
                继续学习
              </Button>
            </div>
          </div>
        </section>
      ) : null}

      {currentPlans.length > 0 ? (
        <section>
          <div className="mb-8 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
              学习计划
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {currentPlans.map((plan) => {
              const percent =
                plan.total > 0 ? Math.round((plan.progress / plan.total) * 100) : 0;
              const reminder = getPlanReminder(plan);
              return (
                <div
                  key={plan.id}
                  onClick={() => navigate(`/graph/${plan.id}`)}
                  className="group relative cursor-pointer overflow-visible rounded-3xl border border-zinc-100 bg-white p-8 shadow-[0_2px_10px_rgba(0,0,0,0.02)] transition-all hover:border-zinc-200 hover:shadow-[0_8px_30px_rgba(0,0,0,0.04)]"
                >
                  <div className="relative z-10 mb-6 flex items-start justify-between">
                    <div className="space-y-3">
                      <div>
                        <h3 className="mb-1 text-lg font-medium text-zinc-900 transition-colors group-hover:text-teal-700">
                          {plan.title}
                        </h3>
                        <p className="text-xs font-medium tracking-wide text-zinc-400">
                          上次学习: {plan.lastAccess || "刚刚"}
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-[11px] font-medium text-zinc-500">
                          {getPlanStatusLabel(plan)}
                        </span>
                        <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-[11px] font-medium text-zinc-500">
                          {getFrequencyLabel(plan.studyFrequency, plan.studyDaysPerWeek)}
                        </span>
                        {plan.targetEndDate ? (
                          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700">
                            截止 {formatPlanDate(plan.targetEndDate)}
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              openDeadlineModal(plan);
                            }}
                            className="rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700 transition-colors hover:bg-amber-100"
                          >
                            设置截止日期
                          </button>
                        )}
                        {reminder ? (
                          <span className="rounded-full bg-teal-50 px-2.5 py-1 text-[11px] font-medium text-teal-700">
                            {reminder.level === "overdue"
                              ? "已拖延"
                              : reminder.level === "due"
                                ? "今日应学"
                                : reminder.level === "deadline"
                                  ? "临近截止"
                                  : reminder.level === "paused"
                                    ? "已暂停提醒"
                                    : "节奏正常"}
                          </span>
                        ) : null}
                        {todayRecommendation?.recommended_node_id &&
                        todayPlan?.id === plan.id ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-2.5 py-1 text-[11px] font-medium text-white">
                            今日推荐
                            <ChevronRight size={12} />
                            下一节点
                          </span>
                        ) : null}
                      </div>
                    </div>

                    <div className="relative" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() =>
                          setActiveMenuPlanId(
                            activeMenuPlanId === plan.id ? null : plan.id,
                          )
                        }
                        className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-50 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-600"
                      >
                        <MoreVertical size={16} />
                      </button>
                      {activeMenuPlanId === plan.id ? (
                        <div className="absolute right-0 top-10 z-20 w-36 rounded-xl border border-zinc-100 bg-white py-1 shadow-xl animate-in fade-in zoom-in-95 duration-100">
                          <button
                            onClick={() => openRenameModal(plan)}
                            className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50"
                          >
                            <Edit3 size={14} /> 重命名
                          </button>
                          <button
                            onClick={() => handlePauseToggle(plan)}
                            className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50"
                          >
                            {plan.status === "paused" ? (
                              <>
                                <Play size={14} /> 恢复
                              </>
                            ) : (
                              <>
                                <Pause size={14} /> 暂停
                              </>
                            )}
                          </button>
                          <button
                            onClick={() => handleArchive(plan.id)}
                            className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50"
                          >
                            <Archive size={14} /> 归档
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="relative z-0">
                    <div className="mb-2 flex justify-between text-xs font-medium text-zinc-400">
                      <span>进度</span>
                      <span className="text-zinc-900">{percent}%</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100">
                      <div
                        className="h-full rounded-full bg-zinc-900 transition-all duration-500 ease-out"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      <Modal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title="确认学习目标"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowConfirmModal(false)}>
              修改输入
            </Button>
            <Button onClick={handleConfirmGeneration}>确认生成</Button>
          </>
        }
      >
        <div className="space-y-6">
          <div className="rounded-2xl border border-zinc-100 bg-zinc-50 p-6">
            <h4 className="mb-3 text-xs font-bold uppercase tracking-widest text-zinc-400">
              识别目标
            </h4>
            <p className="text-xl font-light text-zinc-900">
              {parsedGoal?.interpretation}
            </p>
          </div>

          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-widest text-zinc-400">
              学习目的
            </h4>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {PURPOSE_OPTIONS.map((option) => {
                const selected = learningPurpose === option.id;
                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setLearningPurpose(option.id)}
                    className={`rounded-2xl border p-4 text-left transition-all ${
                      selected
                        ? "border-zinc-900 bg-zinc-900 text-white shadow-lg shadow-zinc-200"
                        : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-300"
                    }`}
                  >
                    <p className="text-sm font-semibold">{option.label}</p>
                    <p
                      className={`mt-2 text-xs leading-5 ${
                        selected ? "text-zinc-300" : "text-zinc-500"
                      }`}
                    >
                      {option.description}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={Boolean(deadlinePlan)}
        onClose={() => {
          if (isSavingDeadline) return;
          setDeadlinePlan(null);
          setDeadlineInput("");
        }}
        title="设置截止日期"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                setDeadlinePlan(null);
                setDeadlineInput("");
              }}
              disabled={isSavingDeadline}
            >
              取消
            </Button>
            <Button onClick={saveDeadline} disabled={isSavingDeadline}>
              {isSavingDeadline ? "保存中..." : "保存日期"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm leading-6 text-zinc-500">
            为「{deadlinePlan?.title || "学习计划"}」设置目标完成日期，今日提醒会据此调整优先级。
          </p>
          <input
            type="date"
            className="w-full rounded-xl border border-zinc-200 px-4 py-3 text-sm outline-none transition-colors focus:border-zinc-400"
            value={deadlineInput}
            onChange={(event) => setDeadlineInput(event.target.value)}
          />
          {deadlinePlan?.targetEndDate ? (
            <button
              type="button"
              onClick={() => setDeadlineInput("")}
              className="text-xs font-medium text-zinc-400 transition-colors hover:text-zinc-700"
            >
              清除截止日期
            </button>
          ) : null}
        </div>
      </Modal>

      <Modal
        isOpen={showRenameModal}
        onClose={() => setShowRenameModal(false)}
        title="重命名计划"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowRenameModal(false)}>
              取消
            </Button>
            <Button onClick={saveNewName} disabled={!newName.trim()}>
              保存
            </Button>
          </>
        }
      >
        <input
          type="text"
          className="w-full rounded-xl border border-zinc-200 px-4 py-3 text-sm outline-none transition-colors focus:border-zinc-400"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="输入新的计划名称"
          autoFocus
        />
      </Modal>
    </div>
  );
};

export default HomePage;
