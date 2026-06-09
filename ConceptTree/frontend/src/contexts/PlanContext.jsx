import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { plansApi, userProfileApi } from "../services/api";
import { createEmptyUserProfile } from "../types";
import { useAuth } from "./AuthContext";
import { useToast } from "./ToastContext";

const PlanContext = createContext(null);
const PLANS_CACHE_KEY = "concept_tree_plans_cache";

export const usePlanContext = () => {
  const context = useContext(PlanContext);
  if (!context) {
    throw new Error("usePlanContext must be used within a PlanProvider");
  }
  return context;
};

const readPlansCache = () => {
  try {
    const raw = window.localStorage.getItem(PLANS_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed?.plans) ? parsed.plans : null;
  } catch {
    return null;
  }
};

const writePlansCache = (plans) => {
  try {
    window.localStorage.setItem(
      PLANS_CACHE_KEY,
      JSON.stringify({ plans: Array.isArray(plans) ? plans : [], updatedAt: Date.now() }),
    );
  } catch {
    // localStorage may be unavailable; keep in-memory state.
  }
};

const mergePlanById = (plans, nextPlan) =>
  plans.map((plan) => (plan.id === nextPlan.id ? { ...plan, ...nextPlan } : plan));

const commitPlans = (updater) => (prev) => {
  const next = typeof updater === "function" ? updater(prev) : updater;
  writePlansCache(next);
  return next;
};

export const PlanProvider = ({ children }) => {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const toast = useToast();

  const [userProfile, setUserProfile] = useState(createEmptyUserProfile());
  const [plans, setPlans] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    const loadPlanData = async () => {
      if (authLoading) return;

      setIsLoading(true);
      try {
        if (isAuthenticated) {
          const [profile, plansList] = await Promise.all([
            userProfileApi.get(),
            plansApi.list(),
          ]);
          if (profile) setUserProfile(profile);
          if (plansList) {
            setPlans(commitPlans(plansList));
            setLoadError(null);
          }
        } else {
          setUserProfile(createEmptyUserProfile());
          setPlans(commitPlans([]));
          setLoadError(null);
        }
      } catch (error) {
        if (error?.status === 401) {
          setUserProfile(createEmptyUserProfile());
          setPlans(commitPlans([]));
          setLoadError(null);
          return;
        }
        const cachedPlans = readPlansCache();
        setLoadError(error);
        if (cachedPlans) {
          setPlans(cachedPlans);
          toast.error("加载学习计划失败，已显示本地缓存");
        } else {
          toast.error("加载学习计划失败，请稍后重试");
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadPlanData();
  }, [authLoading, isAuthenticated, toast]);

  const actions = useMemo(
    () => ({
      setPlans(updater) {
        setPlans(commitPlans(updater));
      },
      async createPlan(input, graphResult, learningPurpose = "apply", metadata = {}) {
        try {
          const newPlan = await plansApi.create({
            title: graphResult.interpretation || input,
            originalInput: input,
            targetNodeId: graphResult.targetNodeId,
            nodes: graphResult.nodes,
            edges: graphResult.edges,
            learning_purpose: learningPurpose,
            ...metadata,
          });
          setPlans(commitPlans((prev) => [newPlan, ...prev]));
          return newPlan;
        } catch (error) {
          toast.error("创建学习计划失败");
          throw error;
        }
      },
      async updatePlan(id, data) {
        try {
          const updated = await plansApi.update(id, data);
          setPlans(commitPlans((prev) => mergePlanById(prev, updated)));
          return updated;
        } catch (error) {
          toast.error("更新学习计划失败");
          throw error;
        }
      },
      async archivePlan(id, reason = "manual") {
        try {
          const updated = await plansApi.archive(id, reason);
          setPlans(commitPlans((prev) => mergePlanById(prev, updated)));
          return updated;
        } catch (error) {
          toast.error("归档计划失败");
          throw error;
        }
      },
      async restorePlan(id) {
        try {
          const updated = await plansApi.restore(id);
          setPlans(commitPlans((prev) => mergePlanById(prev, updated)));
          return updated;
        } catch (error) {
          toast.error("恢复计划失败");
          throw error;
        }
      },
      async pausePlan(id) {
        try {
          const updated = await plansApi.pause(id);
          setPlans(commitPlans((prev) => mergePlanById(prev, updated)));
          return updated;
        } catch (error) {
          toast.error("暂停计划失败");
          throw error;
        }
      },
      async resumePlan(id) {
        try {
          const updated = await plansApi.resume(id);
          setPlans(commitPlans((prev) => mergePlanById(prev, updated)));
          return updated;
        } catch (error) {
          toast.error("恢复学习节奏失败");
          throw error;
        }
      },
      async deletePlan(id) {
        try {
          await plansApi.delete(id);
          setPlans(commitPlans((prev) => prev.filter((plan) => plan.id !== id)));
        } catch (error) {
          toast.error("删除计划失败");
          throw error;
        }
      },
      updatePlanProgress(planId, progress, total) {
        setPlans(
          commitPlans((prev) =>
            prev.map((plan) => (plan.id === planId ? { ...plan, progress, total } : plan)),
          ),
        );
      },
      updateNodeStatusInPlan() {
        // The plan list does not carry full graph details. Progress is refreshed elsewhere.
      },
      async setUserProfile(newProfile) {
        try {
          const updated = await userProfileApi.update(newProfile);
          setUserProfile(updated);
          return updated;
        } catch (error) {
          toast.error("更新用户资料失败");
          throw error;
        }
      },
    }),
    [toast],
  );

  const value = useMemo(
    () => ({
      userProfile,
      plans,
      isLoading,
      loadError,
      actions,
    }),
    [actions, isLoading, loadError, plans, userProfile],
  );

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
};
