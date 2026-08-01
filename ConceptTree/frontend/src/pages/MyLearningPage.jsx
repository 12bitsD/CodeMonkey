import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Archive,
  BarChart3,
  BookOpen,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Search,
  User,
  X,
} from "lucide-react";
import { Badge, Button } from "../components/ui";
import { ChartBar, StatCard } from "../components/common";
import MarkdownContent from "../components/common/MarkdownContent";
import WorkspaceShell from "../components/common/WorkspaceShell";
import { compactPlanTitle } from "../utils/planTitle";
import { formatLastStudied } from "../utils/timeFormatting";
import { useNoteContext } from "../contexts/NoteContext";
import { usePlanContext } from "../contexts/PlanContext";
import { useLanguage } from "../contexts/LanguageContext";
import { statsApi } from "../services/api";

const getTabs = (t) => [
  { id: "profile", label: t("learning.tab.profile"), icon: User },
  { id: "plans", label: t("learning.tab.plans"), icon: Archive },
  { id: "notes", label: t("learning.tab.notes"), icon: BookOpen },
  { id: "stats", label: t("learning.tab.stats"), icon: BarChart3 },
];

const getStatusFilters = (t) => [
  { id: "all", label: t("learning.filter.all") },
  { id: "active", label: t("status.active") },
  { id: "paused", label: t("status.paused") },
  { id: "completed", label: t("status.completed") },
  { id: "archived", label: t("status.archived") },
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

const matchesPlanFilter = (plan, filter) => {
  if (filter === "all") return true;
  if (filter === "completed") {
    return plan.archivedReason === "completed";
  }
  if (filter === "archived") {
    return plan.status === "archived" && plan.archivedReason !== "completed";
  }
  return plan.status === filter;
};

const formatPlanDate = (value, language) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(language === "zh-CN" ? "zh-CN" : "en-US", { year: "numeric", month: "numeric", day: "numeric" });
};

const MyLearningPage = () => {
  const navigate = useNavigate();
  const { language, t } = useLanguage();
  const { userProfile, plans, actions } = usePlanContext();
  const { allNotes, actions: noteActions } = useNoteContext();

  const [activeTab, setActiveTab] = useState("profile");
  const [planFilter, setPlanFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPlanFilter, setSelectedPlanFilter] = useState("all");
  const [isComposing, setIsComposing] = useState(false);
  const [localOccupation, setLocalOccupation] = useState(userProfile?.occupation || "");
  const [localEducation, setLocalEducation] = useState(userProfile?.education || "");
  const [statsData, setStatsData] = useState(null);
  const [distributionData, setDistributionData] = useState([]);
  const tabs = useMemo(() => getTabs(t), [t]);
  const statusFilters = useMemo(() => getStatusFilters(t), [t]);

  useEffect(() => {
    setLocalOccupation(userProfile?.occupation || "");
    setLocalEducation(userProfile?.education || "");
  }, [userProfile?.occupation, userProfile?.education]);

  useEffect(() => {
    if (activeTab !== "stats") return;
    Promise.all([
      statsApi.getOverview().catch(() => null),
      statsApi.getDistribution().catch(() => []),
    ]).then(([overview, distribution]) => {
      if (overview) setStatsData(overview);
      setDistributionData(
        Array.isArray(distribution) ? distribution : distribution.distribution || [],
      );
    });
  }, [activeTab]);

  const filteredPlans = useMemo(
    () => plans.filter((plan) => matchesPlanFilter(plan, planFilter)),
    [planFilter, plans],
  );

  const filteredNotes = useMemo(
    () =>
      allNotes.filter((note) => {
        const matchesPlan =
          selectedPlanFilter === "all" || note.planId === selectedPlanFilter;
        const matchesSearch =
          !searchQuery ||
          note.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
          note.nodeName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          note.planTitle?.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesPlan && matchesSearch;
      }),
    [allNotes, searchQuery, selectedPlanFilter],
  );

  const notesByPlan = useMemo(
    () =>
      filteredNotes.reduce((acc, note) => {
        const key = note.planId;
        if (!acc[key]) {
          acc[key] = { title: note.planTitle || note.planId, notes: [] };
        }
        acc[key].notes.push(note);
        return acc;
      }, {}),
    [filteredNotes],
  );

  const activePlansCount = plans.filter((plan) => plan.status === "active").length;
  const completedPlansCount = plans.filter(
    (plan) => plan.archivedReason === "completed",
  ).length;
  const pausedPlansCount = plans.filter((plan) => plan.status === "paused").length;
  const archivedPlansCount = plans.filter(
    (plan) => plan.status === "archived" && plan.archivedReason !== "completed",
  ).length;

  const handleAddAbility = () => {
    const newAbility = prompt(t("learning.profile.addPrompt"));
    if (!newAbility?.trim()) return;
    actions.setUserProfile({
      ...userProfile,
      abilities: [...(userProfile.abilities || []), newAbility.trim()],
    });
  };

  const handleRemoveAbility = (index) => {
    const nextAbilities = [...(userProfile.abilities || [])];
    nextAbilities.splice(index, 1);
    actions.setUserProfile({ ...userProfile, abilities: nextAbilities });
  };

  const handleResumeOrPause = async (plan) => {
    if (plan.status === "paused") {
      await actions.resumePlan(plan.id);
      return;
    }
    if (plan.status === "active") {
      await actions.pausePlan(plan.id);
    }
  };

  const handleRestore = async (id) => {
    await actions.restorePlan(id);
  };

  return (
    <WorkspaceShell active="learning">
      <div className="notion-page">
        <h1 className="mb-10 text-[clamp(2.25rem,5vw,3.75rem)] font-bold leading-none tracking-[-0.04em] text-[#202020]">
          {t("learning.title")}
        </h1>

      <div className="flex flex-col gap-8">
        <div className="flex w-full flex-wrap gap-1 border-b border-black/[0.1] pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-[background-color,color,transform] duration-150 active:scale-[0.98] ${
                activeTab === tab.id
                  ? "bg-black/[0.055] text-zinc-900"
                  : "text-zinc-500 hover:bg-black/[0.035] hover:text-zinc-900"
              }`}
            >
              <tab.icon size={18} strokeWidth={1.5} />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="min-h-[600px] flex-1 py-2">
          {activeTab === "profile" ? (
            <div className="max-w-2xl space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <section>
                <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                  {t("learning.profile.info")}
                </h2>
                <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">
                      {t("learning.profile.occupation")}
                    </label>
                    <input
                      type="text"
                      value={localOccupation}
                      onChange={(e) => {
                        setLocalOccupation(e.target.value);
                        if (!isComposing) {
                          actions.setUserProfile({
                            ...userProfile,
                            occupation: e.target.value,
                          });
                        }
                      }}
                      onBlur={() =>
                        actions.setUserProfile({
                          ...userProfile,
                          occupation: localOccupation,
                        })
                      }
                      onCompositionStart={() => setIsComposing(true)}
                      onCompositionEnd={() => setIsComposing(false)}
                      placeholder={t("learning.profile.occupationPlaceholder")}
                      className="w-full rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-sm outline-none transition-colors focus:border-zinc-300 focus:bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">
                      {t("learning.profile.education")}
                    </label>
                    <input
                      type="text"
                      value={localEducation}
                      onChange={(e) => {
                        setLocalEducation(e.target.value);
                        if (!isComposing) {
                          actions.setUserProfile({
                            ...userProfile,
                            education: e.target.value,
                          });
                        }
                      }}
                      onBlur={() =>
                        actions.setUserProfile({
                          ...userProfile,
                          education: localEducation,
                        })
                      }
                      onCompositionStart={() => setIsComposing(true)}
                      onCompositionEnd={() => setIsComposing(false)}
                      placeholder={t("learning.profile.educationPlaceholder")}
                      className="w-full rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-sm outline-none transition-colors focus:border-zinc-300 focus:bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">
                      {t("learning.profile.programming")}
                    </label>
                    <select
                      value={userProfile?.programmingLevel || "入门"}
                      onChange={(e) =>
                        actions.setUserProfile({
                          ...userProfile,
                          programmingLevel: e.target.value,
                        })
                      }
                      className="w-full rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-sm outline-none transition-colors focus:border-zinc-300 focus:bg-white"
                    >
                      {[["无基础", "none"], ["入门", "beginner"], ["熟练", "proficient"]].map(([level, key]) => (
                        <option key={level} value={level}>
                          {t(`learning.level.${key}`)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">
                      {t("learning.profile.math")}
                    </label>
                    <select
                      value={userProfile?.mathLevel || "入门"}
                      onChange={(e) =>
                        actions.setUserProfile({
                          ...userProfile,
                          mathLevel: e.target.value,
                        })
                      }
                      className="w-full rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-sm outline-none transition-colors focus:border-zinc-300 focus:bg-white"
                    >
                      {[["无基础", "none"], ["入门", "beginner"], ["熟练", "proficient"]].map(([level, key]) => (
                        <option key={level} value={level}>
                          {t(`learning.level.${key}`)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                  {t("learning.profile.abilities")}
                </h2>
                <div className="flex flex-wrap gap-2">
                  {(userProfile?.abilities || []).map((tag, index) => (
                    <Badge key={`${tag}-${index}`} onDelete={() => handleRemoveAbility(index)}>
                      {tag}
                    </Badge>
                  ))}
                  <button
                    onClick={handleAddAbility}
                    className="flex items-center gap-1 rounded-full border border-dashed border-zinc-300 bg-white px-3 py-1 text-xs font-medium text-zinc-400 transition-colors hover:border-zinc-400 hover:text-zinc-900"
                  >
                    <Plus size={12} /> {t("learning.profile.add")}
                  </button>
                </div>
              </section>

              {(userProfile?.masteredKnowledge || []).length > 0 ? (
                <section>
                  <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                    {t("learning.profile.mastered")}
                  </h2>
                  <div className="flex flex-wrap gap-2">
                    {userProfile.masteredKnowledge.map((knowledge) => (
                      <span
                        key={knowledge}
                        className="rounded-full border border-teal-100 bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700"
                      >
                        {knowledge}
                      </span>
                    ))}
                  </div>
                </section>
              ) : null}
            </div>
          ) : null}

          {activeTab === "plans" ? (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex flex-col gap-4 border-b border-zinc-50 pb-6 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-400">
                    {t("learning.tab.plans")}
                  </h2>
                  <p className="mt-2 text-sm text-zinc-500">
                    {t("learning.plans.help")}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {statusFilters.map((filter) => (
                    <button
                      key={filter.id}
                      onClick={() => setPlanFilter(filter.id)}
                      className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                        planFilter === filter.id
                          ? "bg-zinc-900 text-white"
                          : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200 hover:text-zinc-900"
                      }`}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="border-y border-black/[0.1]">
                {filteredPlans.map((plan) => {
                  const percent =
                    plan.total > 0 ? Math.round((plan.progress / plan.total) * 100) : 0;
                  return (
                    <div
                      key={plan.id}
                      className="notion-row p-5"
                    >
                      <div className="flex flex-col gap-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <h3 className="text-lg font-medium text-zinc-900">
                              {compactPlanTitle(plan.title)}
                            </h3>
                            <p className="mt-1 text-xs text-zinc-400">
                              {t("learning.plans.recent", {
                                value:
                                  formatLastStudied(plan.lastAccess, language) ||
                                  t("home.justNow"),
                              })}
                            </p>
                          </div>
                          <span className="rounded-md bg-[#f7f6f3] px-2.5 py-1 text-xs font-medium text-zinc-600">
                            {getPlanStatusLabel(plan, t)}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          <span className="rounded-md bg-[#f7f6f3] px-2.5 py-1 text-xs font-medium text-zinc-500">
                            {getFrequencyLabel(plan.studyFrequency, plan.studyDaysPerWeek, t)}
                          </span>
                          {plan.targetEndDate ? (
                            <span className="rounded-md bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                              {t("home.deadline", { date: formatPlanDate(plan.targetEndDate, language) })}
                            </span>
                          ) : null}
                          {plan.reminderEnabled ? (
                            <span className="rounded-md bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-700">
                              {t("learning.plans.reminder", { value: plan.reminderTime || t("graph.reminderOn") })}
                            </span>
                          ) : null}
                          {plan.archivedReason ? (
                            <span className="rounded-md bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-500">
                              {t("learning.plans.archiveReason", { value: plan.archivedReason === "completed" ? t("status.completed") : t("learning.plans.manual") })}
                            </span>
                          ) : null}
                        </div>

                        <div>
                          <div className="mb-2 flex justify-between text-xs font-medium text-zinc-400">
                            <span>{t("learning.plans.completion")}</span>
                            <span className="text-zinc-900">{percent}%</span>
                          </div>
                          <div className="h-1.5 overflow-hidden rounded-full bg-zinc-200/70">
                            <div
                              className="h-full rounded-full bg-zinc-900 transition-all duration-500"
                              style={{ width: `${percent}%` }}
                            />
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-3">
                          <Button size="sm" onClick={() => navigate(`/graph/${plan.id}`)}>
                            {t("learning.plans.open")}
                          </Button>
                          {plan.status === "archived" ? (
                            <Button
                              size="sm"
                              variant="outline"
                              icon={RotateCcw}
                              onClick={() => handleRestore(plan.id)}
                            >
                              {t("home.plan.resume")}
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              icon={plan.status === "paused" ? Play : Pause}
                              onClick={() => handleResumeOrPause(plan)}
                            >
                              {plan.status === "paused" ? t("learning.plans.resumeLearning") : t("learning.plans.pause")}
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {filteredPlans.length === 0 ? (
                <div className="py-20 text-center text-zinc-400">
                  <Archive size={48} className="mx-auto mb-4 opacity-20" strokeWidth={1} />
                  {t("learning.plans.empty")}
                </div>
              ) : null}
            </div>
          ) : null}

          {activeTab === "notes" ? (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-50 pb-6">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-400">
                    {t("learning.tab.notes")}
                  </h2>
                  <select
                    value={selectedPlanFilter}
                    onChange={(e) => setSelectedPlanFilter(e.target.value)}
                    className="rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-500 outline-none focus:ring-1 focus:ring-zinc-200"
                  >
                    <option value="all">{t("learning.notes.allPlans")}</option>
                    {plans.map((plan) => (
                      <option key={plan.id} value={plan.id}>
                        {compactPlanTitle(plan.title)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="relative">
                  <Search
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
                  />
                  <input
                    type="text"
                    placeholder={t("learning.notes.search")}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-56 rounded-full bg-zinc-50 py-2 pl-10 pr-4 text-sm transition-all focus:ring-1 focus:ring-zinc-200"
                  />
                </div>
              </div>

              {filteredNotes.length > 0 ? (
                <div className="space-y-8">
                  {Object.entries(notesByPlan).map(([planId, group]) => (
                    <div key={planId}>
                      <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-zinc-400">
                        {group.title}
                      </h3>
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        {group.notes.map((note) => (
                          <div
                            key={note.id}
                            className="group relative rounded-2xl border border-zinc-100/50 bg-zinc-50 p-6 transition-all hover:bg-white hover:shadow-md"
                          >
                            <button
                              onClick={() => noteActions.deleteNote(note.id).catch(() => {})}
                              className="absolute right-3 top-3 rounded-full p-1 text-zinc-300 opacity-0 transition-all hover:bg-red-50 hover:text-red-400 group-hover:opacity-100"
                              title={t("learning.notes.delete")}
                            >
                              <X size={13} />
                            </button>
                            <div
                              className="cursor-pointer"
                              onClick={() =>
                                navigate(
                                  `/graph/${note.planId}${
                                    note.nodeId ? `?node=${note.nodeId}` : ""
                                  }`,
                                )
                              }
                            >
                              <div className="mb-3 flex justify-between pr-4">
                                <div className="flex flex-col gap-0.5">
                                  {note.nodeName ? (
                                    <span className="text-[10px] font-medium text-teal-500">
                                      {note.nodeName}
                                    </span>
                                  ) : null}
                                  <span className="text-[10px] text-zinc-400">
                                    {note.date}
                                  </span>
                                </div>
                              </div>
                              <div className="max-h-28 overflow-hidden">
                                <MarkdownContent
                                  content={note.content}
                                  className="space-y-2 text-sm leading-6 text-zinc-600"
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-20 text-center text-zinc-400">
                  <BookOpen size={48} className="mx-auto mb-4 opacity-20" strokeWidth={1} />
                  {searchQuery || selectedPlanFilter !== "all"
                    ? t("learning.notes.noMatch")
                    : t("learning.notes.empty")}
                </div>
              )}
            </div>
          ) : null}

          {activeTab === "stats" ? (
            <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <section>
                <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                  {t("learning.stats.overview")}
                </h2>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <StatCard
                    label={t("learning.stats.completed")}
                    value={statsData?.summary?.completedPlans ?? completedPlansCount}
                  />
                  <StatCard
                    label={t("learning.stats.active")}
                    value={statsData?.summary?.activePlans ?? activePlansCount}
                  />
                  <StatCard label={t("learning.stats.paused")} value={pausedPlansCount} />
                  <StatCard label={t("learning.stats.archived")} value={archivedPlansCount} />
                </div>
              </section>

              <section>
                <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                  {t("learning.stats.distribution")}
                </h2>
                <div className="space-y-6 rounded-2xl border border-zinc-100 bg-zinc-50 p-8">
                  {distributionData.length > 0 ? (
                    distributionData.map((item, index) => (
                      <ChartBar
                        key={item.domain || index}
                        label={item.domain || t("learning.stats.uncategorized")}
                        value={item.percentage || 0}
                        color={
                          item.domain?.includes("数学")
                            ? "bg-blue-500"
                            : item.domain?.includes("编程")
                              ? "bg-amber-500"
                              : "bg-teal-500"
                        }
                        count={item.count || 0}
                      />
                    ))
                  ) : (
                    <div className="py-8 text-center text-sm text-zinc-400">
                      {t("learning.stats.empty")}
                    </div>
                  )}
                </div>
              </section>
            </div>
          ) : null}
        </div>
      </div>
      </div>
    </WorkspaceShell>
  );
};

export default MyLearningPage;
