import { describe, expect, it } from "vitest";

import { getPlanReminder, getStudyIntervalDays, getTopPlanReminder } from "./planReminders";

describe("planReminders", () => {
  it("computes interval days from frequency", () => {
    expect(getStudyIntervalDays({ studyFrequency: "daily" })).toBe(1);
    expect(getStudyIntervalDays({ studyFrequency: "weekly" })).toBe(7);
    expect(getStudyIntervalDays({ studyFrequency: "custom", studyDaysPerWeek: 2 })).toBe(4);
    expect(getStudyIntervalDays({ studyFrequency: "flexible" })).toBe(3);
  });

  it("marks active plans as overdue when cadence is missed", () => {
    const reminder = getPlanReminder(
      {
        id: "plan_1",
        title: "Transformer",
        status: "active",
        progress: 2,
        total: 8,
        studyFrequency: "daily",
        lastAccess: "2026-04-14T10:00:00.000Z",
      },
      new Date("2026-04-18T12:00:00.000Z"),
    );

    expect(reminder.level).toBe("overdue");
    expect(reminder.overdueDays).toBeGreaterThan(0);
  });

  it("keeps paused plans out of due reminders", () => {
    const reminder = getPlanReminder(
      {
        id: "plan_2",
        title: "Backpropagation",
        status: "paused",
        progress: 1,
        total: 6,
        studyFrequency: "custom",
        studyDaysPerWeek: 3,
      },
      new Date("2026-04-18T12:00:00.000Z"),
    );

    expect(reminder.level).toBe("paused");
    expect(reminder.dueToday).toBe(false);
  });

  it("selects the highest-priority reminder across plans", () => {
    const top = getTopPlanReminder(
      [
        {
          id: "plan_a",
          title: "Linear Algebra",
          status: "active",
          progress: 3,
          total: 10,
          studyFrequency: "weekly",
          lastAccess: "2026-04-16T10:00:00.000Z",
        },
        {
          id: "plan_b",
          title: "Transformer",
          status: "active",
          progress: 1,
          total: 8,
          studyFrequency: "daily",
          targetEndDate: "2026-04-19T00:00:00.000Z",
          lastAccess: "2026-04-15T10:00:00.000Z",
        },
      ],
      new Date("2026-04-18T12:00:00.000Z"),
    );

    expect(top.plan.id).toBe("plan_b");
    expect(top.reminder.level).toBe("deadline");
  });
});
