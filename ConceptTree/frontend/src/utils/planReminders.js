const MS_PER_DAY = 24 * 60 * 60 * 1000;

const normalizeDate = (value, fallback = null) => {
  if (!value) return fallback;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? fallback : date;
};

const daysBetween = (from, to) => {
  const start = new Date(from.getFullYear(), from.getMonth(), from.getDate());
  const end = new Date(to.getFullYear(), to.getMonth(), to.getDate());
  return Math.floor((end - start) / MS_PER_DAY);
};

export const getStudyIntervalDays = (plan) => {
  switch (plan?.studyFrequency) {
    case "daily":
      return 1;
    case "weekly":
      return 7;
    case "custom":
      return Math.max(1, Math.round(7 / Math.max(1, plan?.studyDaysPerWeek || 3)));
    default:
      return 3;
  }
};

export const getPlanReminder = (plan, now = new Date()) => {
  if (!plan) return null;

  const current = normalizeDate(now, new Date());
  const lastAccessDate = normalizeDate(plan.lastAccess, null);
  const targetEndDate = normalizeDate(plan.targetEndDate, null);
  const intervalDays = getStudyIntervalDays(plan);
  const progress = Number(plan.progress || 0);
  const total = Number(plan.total || 0);
  const completionRatio = total > 0 ? progress / total : 0;

  if (plan.archivedReason === "completed") {
    return {
      id: plan.id,
      level: "completed",
      priority: 0,
      headline: `「${plan.title}」已经完成`,
      detail: "这条计划已经学完，可以回顾笔记或开始新的主题。",
      dueToday: false,
      overdueDays: 0,
      intervalDays,
      completionRatio,
    };
  }

  if (plan.status === "archived") {
    return {
      id: plan.id,
      level: "archived",
      priority: 0,
      headline: `「${plan.title}」已归档`,
      detail: "这条计划目前已收纳进历史记录，不会再参与今日提醒。",
      dueToday: false,
      overdueDays: 0,
      intervalDays,
      completionRatio,
    };
  }

  if (plan.status === "paused") {
    return {
      id: plan.id,
      level: "paused",
      priority: 1,
      headline: `「${plan.title}」当前已暂停`,
      detail: "暂停中的计划不会继续催学，你随时可以恢复。",
      dueToday: false,
      overdueDays: 0,
      intervalDays,
      completionRatio,
    };
  }

  const lastStudyDaysAgo = lastAccessDate ? Math.max(0, daysBetween(lastAccessDate, current)) : null;
  const dueToday = lastStudyDaysAgo === null || lastStudyDaysAgo >= intervalDays;
  const overdueDays =
    lastStudyDaysAgo === null ? intervalDays : Math.max(0, lastStudyDaysAgo - intervalDays);
  const daysToDeadline = targetEndDate ? daysBetween(current, targetEndDate) : null;

  let level = "on_track";
  let priority = 2;
  let headline = `今天继续推进「${plan.title}」`;
  let detail = `按当前节奏建议每 ${intervalDays} 天学习一次。`;

  if (dueToday) {
    level = overdueDays > 0 ? "overdue" : "due";
    priority = overdueDays > 0 ? 5 : 4;
    headline =
      overdueDays > 0
        ? `「${plan.title}」已经拖延 ${overdueDays} 天`
        : `今天适合继续学习「${plan.title}」`;
    detail =
      overdueDays > 0
        ? `你上次学习距今 ${lastStudyDaysAgo} 天，已经超过当前节奏。`
        : `按照当前节奏，今天正好适合接着推进这条计划。`;
  }

  if (daysToDeadline !== null && daysToDeadline <= 3 && completionRatio < 1) {
    level = "deadline";
    priority = Math.max(priority, 6);
    headline = `「${plan.title}」距离目标日期只剩 ${Math.max(daysToDeadline, 0)} 天`;
    detail =
      daysToDeadline < 0
        ? "目标日期已经过去，建议尽快恢复节奏或重新调整计划。"
        : "如果你还想按时完成，这几天最好优先推进这条计划。";
  }

  return {
    id: plan.id,
    level,
    priority,
    headline,
    detail,
    dueToday,
    overdueDays,
    intervalDays,
    lastStudyDaysAgo,
    daysToDeadline,
    completionRatio,
  };
};

export const getTopPlanReminder = (plans, now = new Date()) => {
  const reminders = (plans || [])
    .map((plan) => ({ plan, reminder: getPlanReminder(plan, now) }))
    .filter((item) => item.reminder && !["archived", "completed"].includes(item.reminder.level))
    .sort((a, b) => b.reminder.priority - a.reminder.priority);

  return reminders[0] || null;
};
