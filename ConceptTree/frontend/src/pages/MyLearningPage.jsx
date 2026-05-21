import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Archive,
  ArrowLeft,
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
import { useNoteContext } from "../contexts/NoteContext";
import { usePlanContext } from "../contexts/PlanContext";
import { statsApi } from "../services/api";

const tabs = [
  { id: "profile", label: "我的画像", icon: User },
  { id: "plans", label: "学习计划", icon: Archive },
  { id: "notes", label: "全部笔记", icon: BookOpen },
  { id: "stats", label: "学习统计", icon: BarChart3 },
];

const statusFilters = [
  { id: "all", label: "全部" },
  { id: "active", label: "进行中" },
  { id: "paused", label: "已暂停" },
  { id: "completed", label: "已完成" },
  { id: "archived", label: "已归档" },
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

const formatPlanDate = (value) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("zh-CN", { year: "numeric", month: "numeric", day: "numeric" });
};

const MyLearningPage = () => {
  const navigate = useNavigate();
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
    const newAbility = prompt("添加新的能力标签:");
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
    <div className="mx-auto flex min-h-screen max-w-screen-xl flex-col px-6 py-10 md:px-12">
      <div className="mb-12 flex items-center gap-4">
        <button
          onClick={() => navigate("/")}
          className="rounded-full p-2 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-900"
        >
          <ArrowLeft size={24} strokeWidth={1.5} />
        </button>
        <h1 className="text-2xl font-light text-zinc-900">我的学习</h1>
      </div>

      <div className="flex flex-col gap-12 lg:flex-row">
        <div className="w-full flex-shrink-0 space-y-1 lg:w-64">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex w-full items-center gap-4 rounded-xl px-6 py-4 text-sm font-medium transition-all duration-300 ${
                activeTab === tab.id
                  ? "bg-zinc-900 text-white shadow-lg shadow-zinc-200"
                  : "text-zinc-500 hover:bg-white hover:text-zinc-900 hover:shadow-sm"
              }`}
            >
              <tab.icon size={18} strokeWidth={1.5} />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="min-h-[600px] flex-1 rounded-[2rem] border border-zinc-100 bg-white p-10 shadow-[0_4px_20px_rgba(0,0,0,0.02)]">
          {activeTab === "profile" ? (
            <div className="max-w-2xl space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <section>
                <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                  基础信息
                </h2>
                <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">
                      职业 / 身份
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
                      placeholder="例如：大三计算机学生"
                      className="w-full rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-sm outline-none transition-colors focus:border-zinc-300 focus:bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">
                      教育背景
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
                      placeholder="例如：信息工程本科"
                      className="w-full rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-sm outline-none transition-colors focus:border-zinc-300 focus:bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">
                      编程基础
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
                      {["无基础", "入门", "熟练"].map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">
                      数学基础
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
                      {["无基础", "入门", "熟练"].map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                  能力标签
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
                    <Plus size={12} /> 添加
                  </button>
                </div>
              </section>

              {(userProfile?.masteredKnowledge || []).length > 0 ? (
                <section>
                  <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                    已掌握知识
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
                    学习计划
                  </h2>
                  <p className="mt-2 text-sm text-zinc-500">
                    区分进行中、暂停中、已完成和已归档的计划状态。
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

              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                {filteredPlans.map((plan) => {
                  const percent =
                    plan.total > 0 ? Math.round((plan.progress / plan.total) * 100) : 0;
                  return (
                    <div
                      key={plan.id}
                      className="rounded-3xl border border-zinc-100 bg-zinc-50/80 p-6 transition-all hover:border-zinc-200 hover:bg-white hover:shadow-md"
                    >
                      <div className="flex flex-col gap-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <h3 className="text-lg font-medium text-zinc-900">
                              {plan.title}
                            </h3>
                            <p className="mt-1 text-xs text-zinc-400">
                              最近学习 {plan.lastAccess || "刚刚"}
                            </p>
                          </div>
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-zinc-600">
                            {getPlanStatusLabel(plan)}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-zinc-500">
                            {getFrequencyLabel(plan.studyFrequency, plan.studyDaysPerWeek)}
                          </span>
                          {plan.targetEndDate ? (
                            <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                              截止 {formatPlanDate(plan.targetEndDate)}
                            </span>
                          ) : null}
                          {plan.reminderEnabled ? (
                            <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700">
                              提醒 {plan.reminderTime || "已开启"}
                            </span>
                          ) : null}
                          {plan.archivedReason ? (
                            <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-500">
                              归档原因 {plan.archivedReason === "completed" ? "完成" : "手动"}
                            </span>
                          ) : null}
                        </div>

                        <div>
                          <div className="mb-2 flex justify-between text-xs font-medium text-zinc-400">
                            <span>完成度</span>
                            <span className="text-zinc-900">{percent}%</span>
                          </div>
                          <div className="h-2 overflow-hidden rounded-full bg-zinc-200/70">
                            <div
                              className="h-full rounded-full bg-zinc-900 transition-all duration-500"
                              style={{ width: `${percent}%` }}
                            />
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-3">
                          <Button size="sm" onClick={() => navigate(`/graph/${plan.id}`)}>
                            打开图谱
                          </Button>
                          {plan.status === "archived" ? (
                            <Button
                              size="sm"
                              variant="outline"
                              icon={RotateCcw}
                              onClick={() => handleRestore(plan.id)}
                            >
                              恢复
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              icon={plan.status === "paused" ? Play : Pause}
                              onClick={() => handleResumeOrPause(plan)}
                            >
                              {plan.status === "paused" ? "恢复学习" : "暂停计划"}
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
                  当前筛选下还没有学习计划
                </div>
              ) : null}
            </div>
          ) : null}

          {activeTab === "notes" ? (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-50 pb-6">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-400">
                    全部笔记
                  </h2>
                  <select
                    value={selectedPlanFilter}
                    onChange={(e) => setSelectedPlanFilter(e.target.value)}
                    className="rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-500 outline-none focus:ring-1 focus:ring-zinc-200"
                  >
                    <option value="all">全部计划</option>
                    {plans.map((plan) => (
                      <option key={plan.id} value={plan.id}>
                        {plan.title}
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
                    placeholder="搜索笔记..."
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
                              title="删除笔记"
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
                    ? "没有找到匹配的笔记"
                    : "暂时还没有笔记"}
                </div>
              )}
            </div>
          ) : null}

          {activeTab === "stats" ? (
            <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <section>
                <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                  总览
                </h2>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <StatCard
                    label="已完成计划"
                    value={statsData?.summary?.completedPlans ?? completedPlansCount}
                  />
                  <StatCard
                    label="进行中"
                    value={statsData?.summary?.activePlans ?? activePlansCount}
                  />
                  <StatCard label="已暂停" value={pausedPlansCount} />
                  <StatCard label="已归档" value={archivedPlansCount} />
                </div>
              </section>

              <section>
                <h2 className="mb-6 text-sm font-bold uppercase tracking-widest text-zinc-400">
                  知识领域分布
                </h2>
                <div className="space-y-6 rounded-2xl border border-zinc-100 bg-zinc-50 p-8">
                  {distributionData.length > 0 ? (
                    distributionData.map((item, index) => (
                      <ChartBar
                        key={item.domain || index}
                        label={item.domain || "未分类"}
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
                      开始学习后，这里会显示你的知识领域分布
                    </div>
                  )}
                </div>
              </section>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default MyLearningPage;
