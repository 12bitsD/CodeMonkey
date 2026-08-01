import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Archive,
  Bell,
  CalendarDays,
  Edit3,
  MoreVertical,
  Pause,
  Play,
  Sparkles,
  Target,
  ChevronRight,
} from "lucide-react";
import { Button, Modal } from "../components/ui";
import GoalAnalysisLoader from "../components/loaders/GoalAnalysisLoader";
import GraphGenerationLoader from "../components/loaders/GraphGenerationLoader";
import LocalizedDateInput from "../components/common/LocalizedDateInput";
import WorkspaceShell from "../components/common/WorkspaceShell";
import learningMapIllustration from "../assets/illustrations/learning-map.jpg";
import emptyPathIllustration from "../assets/illustrations/empty-path.jpg";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import { usePlanContext } from "../contexts/PlanContext";
import { useToast } from "../contexts/ToastContext";
import { aiApi, graphApi, plansApi } from "../services/api";
import { calculateLayout } from "../utils/layoutEngine";
import { getPlanReminder, getTopPlanReminder } from "../utils/planReminders";
import { compactPlanTitle } from "../utils/planTitle";
import { formatLastStudied } from "../utils/timeFormatting";

const TODAY_RECOMMENDATION_CACHE_KEY = "concept_tree_today_recommendation";

const getTodayCacheDate = () => {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const buildRecommendationCacheKey = (plan, language = "en-US", dateKey = getTodayCacheDate()) => {
  if (!plan?.id) return null;
  return [
    dateKey,
    ...(language === "zh-CN" ? [] : [language]),
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
    () => buildRecommendationCacheKey(todayPlan, language),
    [language, todayPlan],
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
          language,
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
  }, [isAuthenticated, language, todayPlanId, todayPlanStatus, todayRecommendationCacheKey]);

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
      const result = await aiApi.parseGoal(inputText, userProfile, language);
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
      const onGenerationProgress = (evt) => {
        if (evt.type === "node") {
          setStreamProgress({ received: evt.received, total: evt.total || 0 });
        }
      };
      const generationArgs = [
        inputText,
        confirmedInterpretation,
        userProfile,
        learningPurpose,
        onGenerationProgress,
      ];
      if (language !== "zh-CN") generationArgs.push(language);
      const result = await graphApi.generate(...generationArgs);

      const positions = calculateLayout(
        result.nodes || [],
        result.edges || [],
        result.targetNodeId,
      );
      const graphResult = {
        title: parsedGoal?.title?.trim() || confirmedInterpretation,
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

  return (
    <WorkspaceShell active="home">
      <div className="notion-page" onClick={() => setActiveMenuPlanId(null)}>
      <section className="mb-14 grid items-center gap-10 lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-16">
        <div>
          <p className="notion-section-label mb-3">
            {t("home.eyebrow")}
          </p>
          <h1 className="max-w-3xl text-[clamp(2.65rem,6vw,4.65rem)] font-bold leading-[1.02] tracking-[-0.05em] text-[#1d1d1f]">
            {t("home.title.before")}<span>{t("home.title.emphasis")}</span>{t("home.title.after")}
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-[var(--color-label-secondary)] sm:text-lg">
            {t("home.subtitle")}
          </p>
        </div>
        <img
          src={learningMapIllustration}
          alt=""
          className="notion-illustration mx-auto hidden w-full max-w-[330px] lg:block"
        />
      </section>

      <section className="mb-20 w-full max-w-4xl">

        {isLoadingScene ? (
          <div className="relative min-h-[500px] overflow-hidden rounded-xl border border-black/[0.1] bg-[#fbfbfa] sm:min-h-[460px]">
            {isAnalyzing ? <GoalAnalysisLoader step={analysisStep} /> : null}
            {isGenerating ? (
              <GraphGenerationLoader
                readyCount={streamProgress?.received || 0}
                totalCount={streamProgress?.total || 0}
              />
            ) : null}
          </div>
        ) : (
          <div className="group relative overflow-hidden rounded-[22px] border border-black/[0.12] bg-white/95 shadow-[0_14px_40px_rgba(15,15,15,0.07),0_2px_8px_rgba(15,15,15,0.04)] transition-[border-color,box-shadow,transform] duration-200 focus-within:border-black/40 focus-within:shadow-[0_0_0_4px_rgba(0,0,0,0.07),0_18px_48px_rgba(15,15,15,0.09)]">
            <textarea
              className="h-40 w-full resize-none bg-transparent px-6 pb-4 pt-6 text-base font-normal leading-7 text-[#1d1d1f] outline-none placeholder:text-[#9a9aa0] focus-visible:outline-none sm:h-44 sm:px-7 sm:pt-7 sm:text-lg"
              placeholder={t("home.goal.placeholder")}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isAnalyzing || isGenerating}
            />

            <div className="flex min-h-[68px] items-center justify-between gap-4 border-t border-black/[0.06] bg-[#fbfbfd]/80 px-4 py-3 sm:px-5">
              <div className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
                {userProfile?.abilities?.slice(0, 2).map((tag) => (
                  <span
                    key={tag}
                    className="truncate rounded-full bg-black/[0.045] px-3 py-1.5 text-xs font-medium text-[#6e6e73]"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <Button
                onClick={handleStartAnalysis}
                disabled={!inputText.trim() || isAnalyzing || isGenerating}
                size="lg"
                icon={Sparkles}
                className="shrink-0 rounded-full bg-[#1d1d1f] px-5 shadow-none hover:bg-black focus-visible:outline-black"
              >
                {isAnalyzing ? t("home.goal.analyzing") : t("home.goal.generate")}
              </Button>
            </div>
          </div>
        )}

        {!inputText && !isLoadingScene ? (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {[
              t("home.suggestion.backprop"),
              t("home.suggestion.python"),
              t("home.suggestion.transformer"),
            ].map((text) => (
              <button
                key={text}
                onClick={() => setInputText(text)}
                className="min-h-9 rounded-full border border-black/[0.09] bg-white/80 px-3.5 py-1.5 text-sm text-[#6e6e73] shadow-[0_1px_2px_rgba(15,15,15,0.025)] transition-[background-color,border-color,color,transform] duration-150 hover:border-black/[0.15] hover:bg-white hover:text-[#1d1d1f] active:scale-[0.98]"
              >
                {text}
              </button>
            ))}
          </div>
        ) : null}
      </section>

      {todayPlan && todayReminder ? (
        <section className="relative mb-14 overflow-hidden rounded-xl border border-black/10 bg-[#202020] p-6 text-white shadow-[0_1px_2px_rgba(0,0,0,0.12)] sm:p-8">
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div className="min-w-0 flex-1 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-400">
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
              <Button variant="secondary" onClick={() => navigate(`/graph/${todayPlan.id}`)} size="sm">
                {t("home.continue")}
              </Button>
            </div>
          </div>
        </section>
      ) : null}

      {currentPlans.length > 0 ? (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="notion-section-label">
              {t("home.plans")}
            </h2>
          </div>

          <div className="overflow-visible border-y border-black/[0.1]">
            {currentPlans.map((plan) => {
              const percent =
                plan.total > 0 ? Math.round((plan.progress / plan.total) * 100) : 0;
              const reminder = getPlanReminder(plan);
              return (
                <div
                  key={plan.id}
                  onClick={() => navigate(`/graph/${plan.id}`)}
                  className="notion-row group relative cursor-pointer overflow-visible px-3 py-5 sm:px-4"
                >
                  <div className="relative z-10 mb-6 flex items-start justify-between">
                    <div className="space-y-3">
                      <div>
                        <h3 className="mb-1 text-base font-semibold text-zinc-900" title={plan.title}>
                          {compactPlanTitle(plan.title)}
                        </h3>
                        <p className="text-xs font-medium tracking-wide text-zinc-400">
                          {t("home.lastStudied", {
                            value:
                              formatLastStudied(plan.lastAccess, language) ||
                              t("home.justNow"),
                          })}
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
                        className="flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 transition-[background-color,color,transform] duration-150 hover:bg-black/[0.06] hover:text-zinc-700 active:scale-[0.96]"
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
      ) : (
        <section className="border-t border-black/[0.1] py-10">
          <div className="flex flex-col items-center text-center">
            <img
              src={emptyPathIllustration}
              alt=""
              className="notion-illustration mb-4 w-full max-w-[260px]"
            />
            <h2 className="text-lg font-semibold text-[#202020]">{t("home.plans")}</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-[#6f6e6b]">{t("home.subtitle")}</p>
          </div>
        </section>
      )}

      <Modal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title={t("home.goal.confirmTitle")}
        className="max-w-2xl"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowConfirmModal(false)}>
              {t("home.goal.edit")}
            </Button>
            <Button onClick={handleConfirmGeneration}>{t("home.goal.confirm")}</Button>
          </>
        }
      >
        <div className="space-y-5">
          <div className="rounded-xl border border-black/[0.07] bg-[#fbfbfa] p-5">
            <h4 className="mb-2 text-[0.65625rem] font-semibold uppercase tracking-[0.075em] text-[#8f8e8b]">
              {t("home.goal.interpreted")}
            </h4>
            <p className="text-[0.9375rem] font-normal leading-6 text-[#202020]">
              {parsedGoal?.interpretation}
            </p>
          </div>

          <div className="space-y-3">
            <h4 className="text-[0.65625rem] font-semibold uppercase tracking-[0.075em] text-[#8f8e8b]">
              {t("home.goal.purpose")}
            </h4>
            <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
              {purposeOptions.map((option) => {
                const selected = learningPurpose === option.id;
                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setLearningPurpose(option.id)}
                    className={`rounded-xl border p-3.5 text-left transition-[background-color,border-color,color,transform,box-shadow] duration-150 active:scale-[0.98] ${
                      selected
                        ? "border-[#202020] bg-[#202020] text-white shadow-[0_4px_12px_rgba(15,15,15,0.12)]"
                        : "border-black/[0.1] bg-white text-[#5f5e5b] hover:border-black/25"
                    }`}
                  >
                    <p className="text-[0.8125rem] font-semibold leading-5">{option.label}</p>
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
          <LocalizedDateInput
            aria-label={t("home.deadline.title")}
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
    </WorkspaceShell>
  );
};

export default HomePage;
