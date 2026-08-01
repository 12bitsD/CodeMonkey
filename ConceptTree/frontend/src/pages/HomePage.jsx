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
import LanguageToggle from "../components/common/LanguageToggle";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import { usePlanContext } from "../contexts/PlanContext";
import { useToast } from "../contexts/ToastContext";
import { aiApi, graphApi, plansApi } from "../services/api";
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

const getPurposeOptions = (t) => [
  { id: "explore", label: t("home.purpose.explore"), description: t("home.purpose.exploreHelp") },
  { id: "apply", label: t("home.purpose.apply"), description: t("home.purpose.applyHelp") },
  { id: "master", label: t("home.purpose.master"), description: t("home.purpose.masterHelp") },
];

const getFrequencyLabel = (frequency, daysPerWeek, t) => {
  switch (frequency) {
    case "daily":
      return t("frequency.daily");
    case "weekly":
      return t("frequency.weekly");
    case "custom":
      return t("frequency.custom", { count: daysPerWeek || 3 });
    default:
      return t("frequency.flexible");
  }
};

const getPlanStatusLabel = (plan, t) => {
  if (plan.status === "paused") return t("status.paused");
  if (plan.archivedReason === "completed") return t("status.completed");
  if (plan.status === "archived") return t("status.archived");
  return t("status.active");
};

const formatPlanDate = (value, language) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(language === "zh-CN" ? "zh-CN" : "en-US", {
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

const getReminderCopy = (reminder, plan, t) => {
  const variables = {
    name: plan?.title || "",
    count:
      reminder.level === "deadline"
        ? Math.max(reminder.daysToDeadline || 0, 0)
        : reminder.level === "overdue"
          ? reminder.overdueDays
          : reminder.intervalDays,
  };
  const headlineKey = `reminder.headline.${
    reminder.level === "on_track" ? "onTrack" : reminder.level
  }`;
  let detailKey = `reminder.detail.${
    reminder.level === "on_track" ? "onTrack" : reminder.level
  }`;
  if (reminder.level === "deadline" && reminder.daysToDeadline < 0) {
    detailKey = "reminder.detail.deadlinePast";
  }
  return { headline: t(headlineKey, variables), detail: t(detailKey, variables) };
};

const HomePage = () => {
  const navigate = useNavigate();
  const { language, t } = useLanguage();
  const { userProfile, plans, actions } = usePlanContext();
  const { isAuthenticated, logout } = useAuth();
  const toast = useToast();

  const [inputText, setInputText] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamProgress, setStreamProgress] = useState(null);
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
  const purposeOptions = useMemo(() => getPurposeOptions(t), [t]);

  const currentPlans = useMemo(
    () => plans.filter((plan) => plan.status === "active" || plan.status === "paused"),
    [plans],
  );

  const topReminder = useMemo(() => getTopPlanReminder(currentPlans), [currentPlans]);
  const todayPlan = topReminder?.plan || currentPlans[0] || null;
  const todayReminder = topReminder?.reminder || (todayPlan ? getPlanReminder(todayPlan) : null);
  const todayReminderCopy = todayReminder
    ? getReminderCopy(todayReminder, todayPlan, t)
    : null;
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
      toast.success(nextTargetEndDate ? t("toast.deadlineUpdated") : t("toast.deadlineCleared"));
    } catch (error) {
      actions.setPlans(previousPlans);
      toast.error(t("toast.deadlineFailed"));
    }
  };

  const redirectToLogin = async (message) => {
    if (message) toast.error(message);
    if (isAuthenticated) {
      await logout();
    }
    navigate(`/auth?redirect=${encodeURIComponent("/")}`);
  };

  const handleStartAnalysis = async () => {
    if (!inputText.trim()) return;
    if (!isAuthenticated) {
      toast.info(t("toast.signInForAi"));
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
      if (error?.status === 401) {
        await redirectToLogin(t("toast.sessionExpired"));
      } else {
        toast.error(t("toast.parseFailed"));
      }
    } finally {
      clearInterval(interval);
      setIsAnalyzing(false);
    }
  };

  const handleConfirmGeneration = async () => {
    const confirmedInterpretation = parsedGoal?.interpretation?.trim() || inputText;
    setShowConfirmModal(false);
    setIsGenerating(true);
    setStreamProgress(null);

    try {
      const result = await graphApi.generate(
        inputText,
        confirmedInterpretation,
        userProfile,
        learningPurpose,
        (evt) => {
          if (evt.type === "node") {
            setStreamProgress({ received: evt.received, total: evt.total || 0 });
          }
        },
      );

      const positions = calculateLayout(
        result.nodes || [],
        result.edges || [],
        result.targetNodeId,
      );
      const graphResult = {
        interpretation: confirmedInterpretation,
        targetNodeId: result.targetNodeId,
        edges: result.edges || [],
        nodes: (result.nodes || []).map((node) => ({
          ...node,
          status: "unlearned",
          x: positions[node.id]?.x ?? node.x ?? 0,
          y: positions[node.id]?.y ?? node.y ?? 0,
          isTarget: node.id === result.targetNodeId,
        })),
      };

      const newPlan = await actions.createPlan(inputText, graphResult, learningPurpose);

      setIsGenerating(false);
      setStreamProgress(null);
      navigate(`/graph/${newPlan.id}`);
      setInputText("");
    } catch (error) {
      if (error?.status === 401) {
        await redirectToLogin(t("toast.sessionExpired"));
      } else {
        toast.error(t("toast.graphFailed"));
      }
      setIsGenerating(false);
      setStreamProgress(null);
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
      className="relative mx-auto flex min-h-screen max-w-[1440px] flex-col px-4 pb-16 pt-4 sm:px-6 md:px-10"
      onClick={() => setActiveMenuPlanId(null)}
    >
      <header className="apple-toolbar sticky top-4 z-40 mb-16 flex items-center justify-between rounded-[20px] px-3 py-2.5 sm:px-4">
        <div
          className="group flex cursor-pointer items-center gap-3"
          onClick={() => navigate("/")}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-[11px] bg-gradient-to-b from-[#1687ff] to-[#006ee6] text-white shadow-[0_4px_12px_rgba(0,122,255,0.24)] transition-transform duration-150 group-active:scale-[0.96]">
            <BrainCircuit size={19} strokeWidth={1.8} />
          </div>
          <span className="text-[15px] font-semibold tracking-[-0.01em] text-[var(--color-label)] sm:text-base">
            PathFinder
          </span>
        </div>

        {!isAuthenticated ? (
          <div className="flex items-center gap-2">
            <LanguageToggle />
            <button
              onClick={() => navigate("/auth")}
              className="min-h-9 rounded-full bg-[#007AFF] px-4 py-2 text-sm font-semibold text-white shadow-[0_2px_8px_rgba(0,122,255,0.22)] transition-[background-color,transform] duration-150 hover:bg-[#0071E3] active:scale-[0.97] sm:px-5"
            >
              {t("nav.signIn")}
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <LanguageToggle className="hidden sm:inline-flex" />
            <div className="flex items-center gap-1 rounded-full border border-black/[0.06] bg-white/70 p-1 shadow-sm">
            <button
              onClick={() => navigate("/my-learning")}
              className="flex min-h-8 items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium text-zinc-600 transition-[background-color,color,transform] duration-150 hover:bg-black/[0.05] hover:text-zinc-900 active:scale-[0.97] sm:px-4"
            >
              <User size={16} strokeWidth={2} />
              <span className="hidden sm:inline">{t("nav.myLearning")}</span>
            </button>
            <button
              onClick={handleLogout}
              className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-[background-color,color,transform] duration-150 hover:bg-red-50 hover:text-red-600 active:scale-[0.94]"
              title={t("nav.signOut")}
              aria-label={t("nav.signOut")}
            >
              <LogOut size={16} strokeWidth={2} />
            </button>
            </div>
          </div>
        )}
      </header>

      <section className="mx-auto mb-24 flex w-full max-w-4xl flex-1 flex-col justify-center pt-8">
        <div className="mb-10 space-y-4 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#007AFF]">
            {t("home.eyebrow")}
          </p>
          <h1 className="text-[clamp(2.5rem,6vw,4.75rem)] font-semibold leading-[1.02] tracking-[-0.055em] text-[var(--color-label)]">
            {t("home.title.before")}<span className="text-[#007AFF]">{t("home.title.emphasis")}</span>{t("home.title.after")}
          </h1>
          <p className="mx-auto max-w-2xl text-lg font-normal leading-7 text-[var(--color-label-secondary)]">
            {t("home.subtitle")}
          </p>
        </div>

        {isLoadingScene ? (
          <div className="relative min-h-[430px] overflow-hidden rounded-3xl border border-zinc-100 bg-white shadow-[0_8px_40px_rgba(0,0,0,0.04)]">
            {isAnalyzing ? <GoalAnalysisLoader step={analysisStep} /> : null}
            {isGenerating ? (
              <GraphGenerationLoader
                readyCount={streamProgress?.received || 0}
                totalCount={streamProgress?.total || 0}
              />
            ) : null}
          </div>
        ) : (
          <div className="apple-card group relative overflow-hidden rounded-[28px] p-2 transition-[border-color,box-shadow,transform] duration-200 focus-within:border-blue-300/70 focus-within:shadow-[0_16px_50px_rgba(0,93,200,0.12)]">
          <textarea
            className="h-44 w-full resize-none bg-transparent p-5 text-lg font-normal leading-relaxed text-zinc-800 outline-none placeholder:text-zinc-400 sm:p-7 sm:text-xl"
            placeholder={t("home.goal.placeholder")}
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
              {isAnalyzing ? t("home.goal.analyzing") : t("home.goal.generate")}
            </Button>
          </div>
          </div>
        )}

        {!inputText && !isLoadingScene ? (
          <div className="mt-7 flex flex-wrap items-center justify-center gap-2.5">
            {[
              t("home.suggestion.backprop"),
              t("home.suggestion.python"),
              t("home.suggestion.transformer"),
            ].map((text) => (
              <button
                key={text}
                onClick={() => setInputText(text)}
                className="min-h-10 rounded-full border border-black/[0.08] bg-white/60 px-4 py-2 text-sm text-zinc-600 shadow-sm backdrop-blur-xl transition-[background-color,border-color,color,transform] duration-150 hover:border-black/[0.14] hover:bg-white hover:text-zinc-900 active:scale-[0.97]"
              >
                {text}
              </button>
            ))}
          </div>
        ) : null}
      </section>

      {todayPlan && todayReminder ? (
        <section className="relative mb-10 overflow-hidden rounded-[30px] border border-white/10 bg-[#17171a] p-6 text-white shadow-[0_20px_60px_rgba(0,0,0,0.16)] sm:p-8">
          <div className="pointer-events-none absolute -right-24 -top-32 h-80 w-80 rounded-full bg-blue-500/25 blur-3xl" />
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div className="min-w-0 flex-1 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-300">
                {t("home.today")}
              </p>
              <h2 className="max-w-3xl text-2xl font-semibold leading-snug text-white md:text-[26px]">
                {todayReminderCopy?.headline}
              </h2>
              <p className="max-w-2xl text-sm leading-6 text-zinc-300">
                {todayReminderCopy?.detail}
              </p>
              <div className="flex flex-wrap items-center gap-2 text-[11px] font-medium text-zinc-300">
                <span
                  className={`inline-flex h-6 items-center rounded-full border px-3 ${getReminderTone(
                    todayReminder.level,
                  )}`}
                >
                  {getPlanStatusLabel(todayPlan, t)}
                </span>
                <span className="inline-flex h-6 items-center gap-1 rounded-full bg-white/10 px-3">
                  <CalendarDays size={12} />
                  {getFrequencyLabel(
                    todayPlan.studyFrequency,
                    todayPlan.studyDaysPerWeek,
                    t,
                  )}
                </span>
                {todayPlan.reminderEnabled ? (
                  <span className="inline-flex h-6 items-center gap-1 rounded-full bg-white/10 px-3">
                    <Bell size={12} />
                    {todayPlan.reminderTime || t("home.reminderOn")}
                  </span>
                ) : null}
                {todayPlan.targetEndDate ? (
                  <span className="inline-flex h-6 items-center gap-1 rounded-full bg-white/10 px-3">
                    <Target size={12} />
                    {t("home.deadline", { date: formatPlanDate(todayPlan.targetEndDate, language) })}
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => openDeadlineModal(todayPlan)}
                    className="inline-flex h-6 items-center gap-1 rounded-full bg-white/10 px-3 transition-colors hover:bg-white/15 hover:text-white"
                  >
                    <Target size={12} />
                    {t("home.setDeadline")}
                  </button>
                )}
              </div>
              {todayRecommendation?.recommended_node_id ? (
                <div className="max-w-5xl rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400">
                    {todayRecommendation.recommendation_source === "local"
                      ? t("home.recommendation.local")
                      : t("home.recommendation.ai")}
                  </p>
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold leading-6 text-white">
                        {t("home.recommendation.heading")}
                      </p>
                      <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-300">
                        {todayRecommendation.reason || t("home.recommendation.fallback")}
                      </p>
                      {todayRecommendation.recommendation_source === "local" ? (
                        <p className="mt-1 text-xs leading-5 text-zinc-500">
                          {t("home.recommendation.localHelp")}
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
                      className="inline-flex h-11 w-full shrink-0 items-center justify-center rounded-full bg-white px-5 text-sm font-semibold leading-none text-zinc-900 transition-[background-color,transform] duration-150 hover:bg-zinc-100 active:scale-[0.97] md:w-auto"
                    >
                      {t("home.goLearn")}
                    </button>
                  </div>
                </div>
              ) : isLoadingRecommendation ? (
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-zinc-300">
                  {t("home.recommendation.loading")}
                </div>
              ) : null}
            </div>
            <div className="space-y-3 text-sm text-zinc-300 md:text-right">
              <p>
                {t("home.currentProgress")}{" "}
                <span className="font-semibold text-white">
                  {todayPlan.progress}/{todayPlan.total || 0}
                </span>
              </p>
              <p>
                {todayReminder.lastStudyDaysAgo === null
                  ? t("home.neverStarted")
                  : t("home.daysSince", { count: todayReminder.lastStudyDaysAgo })}
              </p>
              <Button onClick={() => navigate(`/graph/${todayPlan.id}`)} size="sm">
                {t("home.continue")}
              </Button>
            </div>
          </div>
        </section>
      ) : null}

      {currentPlans.length > 0 ? (
        <section>
          <div className="mb-8 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
              {t("home.plans")}
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
                  className="apple-card group relative cursor-pointer overflow-visible rounded-[26px] p-6 transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-white hover:shadow-[0_18px_45px_rgba(0,0,0,0.09)] active:translate-y-0 sm:p-7"
                >
                  <div className="relative z-10 mb-6 flex items-start justify-between">
                    <div className="space-y-3">
                      <div>
                        <h3 className="mb-1 text-lg font-medium text-zinc-900 transition-colors group-hover:text-teal-700">
                          {plan.title}
                        </h3>
                        <p className="text-xs font-medium tracking-wide text-zinc-400">
                          {t("home.lastStudied", { value: plan.lastAccess || t("home.justNow") })}
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-[11px] font-medium text-zinc-500">
                          {getPlanStatusLabel(plan, t)}
                        </span>
                        <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-[11px] font-medium text-zinc-500">
                          {getFrequencyLabel(plan.studyFrequency, plan.studyDaysPerWeek, t)}
                        </span>
                        {plan.targetEndDate ? (
                          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700">
                            {t("home.deadline", { date: formatPlanDate(plan.targetEndDate, language) })}
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
                            {t("home.setDeadline")}
                          </button>
                        )}
                        {reminder ? (
                          <span className="rounded-full bg-teal-50 px-2.5 py-1 text-[11px] font-medium text-teal-700">
                            {reminder.level === "overdue"
                              ? t("reminder.overdue")
                              : reminder.level === "due"
                                ? t("reminder.due")
                                : reminder.level === "deadline"
                                  ? t("reminder.deadline")
                                  : reminder.level === "paused"
                                    ? t("reminder.paused")
                                    : t("reminder.normal")}
                          </span>
                        ) : null}
                        {todayRecommendation?.recommended_node_id &&
                        todayPlan?.id === plan.id ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-2.5 py-1 text-[11px] font-medium text-white">
                            {t("home.plan.today")}
                            <ChevronRight size={12} />
                            {t("home.plan.next")}
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
                        className="flex h-9 w-9 items-center justify-center rounded-full bg-black/[0.04] text-zinc-500 transition-[background-color,color,transform] duration-150 hover:bg-black/[0.08] hover:text-zinc-700 active:scale-[0.94]"
                      >
                        <MoreVertical size={16} />
                      </button>
                      {activeMenuPlanId === plan.id ? (
                        <div className="absolute right-0 top-10 z-20 w-36 rounded-xl border border-zinc-100 bg-white py-1 shadow-xl animate-in fade-in zoom-in-95 duration-100">
                          <button
                            onClick={() => openRenameModal(plan)}
                            className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50"
                          >
                            <Edit3 size={14} /> {t("home.plan.rename")}
                          </button>
                          <button
                            onClick={() => handlePauseToggle(plan)}
                            className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50"
                          >
                            {plan.status === "paused" ? (
                              <>
                                <Play size={14} /> {t("home.plan.resume")}
                              </>
                            ) : (
                              <>
                                <Pause size={14} /> {t("home.plan.pause")}
                              </>
                            )}
                          </button>
                          <button
                            onClick={() => handleArchive(plan.id)}
                            className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-50"
                          >
                            <Archive size={14} /> {t("home.plan.archive")}
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="relative z-0">
                    <div className="mb-2 flex justify-between text-xs font-medium text-zinc-400">
                      <span>{t("home.progress")}</span>
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
        title={t("home.goal.confirmTitle")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowConfirmModal(false)}>
              {t("home.goal.edit")}
            </Button>
            <Button onClick={handleConfirmGeneration}>{t("home.goal.confirm")}</Button>
          </>
        }
      >
        <div className="space-y-6">
          <div className="rounded-2xl border border-zinc-100 bg-zinc-50 p-6">
            <h4 className="mb-3 text-xs font-bold uppercase tracking-widest text-zinc-400">
              {t("home.goal.interpreted")}
            </h4>
            <p className="text-xl font-light text-zinc-900">
              {parsedGoal?.interpretation}
            </p>
          </div>

          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-widest text-zinc-400">
              {t("home.goal.purpose")}
            </h4>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {purposeOptions.map((option) => {
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
        title={t("home.deadline.title")}
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
              {t("common.cancel")}
            </Button>
            <Button onClick={saveDeadline} disabled={isSavingDeadline}>
              {isSavingDeadline ? t("common.saving") : t("home.deadline.save")}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm leading-6 text-zinc-500">
            {t("home.deadline.help", { name: deadlinePlan?.title || t("home.plans") })}
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
              {t("home.deadline.clear")}
            </button>
          ) : null}
        </div>
      </Modal>

      <Modal
        isOpen={showRenameModal}
        onClose={() => setShowRenameModal(false)}
        title={t("home.rename.title")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowRenameModal(false)}>
              {t("common.cancel")}
            </Button>
            <Button onClick={saveNewName} disabled={!newName.trim()}>
              {t("common.save")}
            </Button>
          </>
        }
      >
        <input
          type="text"
          className="w-full rounded-xl border border-zinc-200 px-4 py-3 text-sm outline-none transition-colors focus:border-zinc-400"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={t("home.rename.placeholder")}
          autoFocus
        />
      </Modal>
    </div>
  );
};

export default HomePage;
