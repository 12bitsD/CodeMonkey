import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { plansApi, userProfileApi } from "../services/api";
import { createEmptyUserProfile } from "../types";
import { useAuth } from "./AuthContext";
import { useToast } from "./ToastContext";

const PlanContext = createContext(null);

export const usePlanContext = () => {
  const context = useContext(PlanContext);
  if (!context) {
    throw new Error("usePlanContext must be used within a PlanProvider");
  }
  return context;
};

export const PlanProvider = ({ children }) => {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const toast = useToast();
  const showErrorToast = toast.error;

  const [userProfile, setUserProfile] = useState(createEmptyUserProfile());
  const [plans, setPlans] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

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
          if (plansList) setPlans(plansList);
        } else {
          setUserProfile(createEmptyUserProfile());
          setPlans([]);
        }
      } catch (error) {
        showErrorToast("加载计划数据失败，请刷新后重试");
      } finally {
        setIsLoading(false);
      }
    };

    loadPlanData();
  }, [authLoading, isAuthenticated, showErrorToast]);

  const actions = useMemo(
    () => ({
      setPlans,
      async createPlan(input, graphResult, learningPurpose = "apply") {
        try {
          const newPlan = await plansApi.create({
            title: graphResult.interpretation || input,
            originalInput: input,
            targetNodeId: graphResult.targetNodeId,
            nodes: graphResult.nodes,
            edges: graphResult.edges,
            learning_purpose: learningPurpose,
          });
          setPlans((prev) => [newPlan, ...prev]);
          return newPlan;
        } catch (error) {
          showErrorToast("创建计划失败");
          throw error;
        }
      },
      async updatePlan(id, data) {
        try {
          const updated = await plansApi.update(id, data);
          setPlans((prev) =>
            prev.map((plan) => (plan.id === id ? { ...plan, ...updated } : plan)),
          );
          return updated;
        } catch (error) {
          showErrorToast("更新计划失败");
          throw error;
        }
      },
      async archivePlan(id) {
        try {
          await plansApi.archive(id);
          setPlans((prev) =>
            prev.map((plan) => (plan.id === id ? { ...plan, status: "archived" } : plan)),
          );
        } catch (error) {
          showErrorToast("归档计划失败");
          throw error;
        }
      },
      async deletePlan(id) {
        try {
          await plansApi.delete(id);
          setPlans((prev) => prev.filter((plan) => plan.id !== id));
        } catch (error) {
          showErrorToast("删除计划失败");
          throw error;
        }
      },
      async restorePlan(id) {
        try {
          await plansApi.restore(id);
          setPlans((prev) =>
            prev.map((plan) => (plan.id === id ? { ...plan, status: "active" } : plan)),
          );
        } catch (error) {
          showErrorToast("恢复计划失败");
          throw error;
        }
      },
      updatePlanProgress(planId, progress, total) {
        setPlans((prev) =>
          prev.map((plan) => (plan.id === planId ? { ...plan, progress, total } : plan)),
        );
      },
      updateNodeStatusInPlan() {
        // Plan list items do not include node details; progress sync happens elsewhere.
      },
      async setUserProfile(newProfile) {
        try {
          const updated = await userProfileApi.update(newProfile);
          setUserProfile(updated);
          return updated;
        } catch (error) {
          showErrorToast("更新用户画像失败");
          throw error;
        }
      },
    }),
    [showErrorToast],
  );

  const value = useMemo(
    () => ({
      userProfile,
      plans,
      isLoading,
      actions,
    }),
    [actions, isLoading, plans, userProfile],
  );

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
};
