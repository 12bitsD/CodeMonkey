/**
 * Global application state context — user profile, learning plans, and notes.
 *
 * `AppContext` is the central store for data that multiple pages need:
 * the authenticated user's profile, their list of learning plans, and all
 * personal notes attached to plan nodes.
 *
 * Data is loaded from the backend **only when the user is authenticated**.
 * When the user is not logged in, all state is reset to empty defaults so
 * pages always receive a valid (if empty) data shape.
 *
 * Context value shape:
 * ```js
 * {
 *   userProfile: UserProfile,   // learning background (occupation, levels, etc.)
 *   plans: Plan[],              // all plans for the current user
 *   allNotes: Note[],           // all notes across all plans
 *   isLoading: boolean,         // true while initial data fetch is in flight
 *   actions: {
 *     setUserProfile(newProfile): Promise<void>,
 *     setPlans(plans): void,          // direct state setter (advanced use)
 *     createPlan(input, graphResult): Promise<Plan>,
 *     updatePlan(id, data): Promise<Plan>,
 *     archivePlan(id): Promise<void>,
 *     deletePlan(id): Promise<void>,
 *     addNote(planId, nodeId, content): Promise<Note>,
 *     deleteNote(noteId): Promise<void>,
 *     updateNodeStatusInPlan(planId, nodeId, status): void,
 *   }
 * }
 * ```
 *
 * Important: `updateNodeStatusInPlan` is **local-only** (no API call). The
 * caller must also call `graphApi.updateNodeStatus` to persist the change.
 *
 * @module contexts/AppContext
 */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { userProfileApi, plansApi, notesApi } from '../services/api';
import { createEmptyUserProfile } from '../types';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

const AppContext = createContext();

/**
 * Accesses the global app context from any child component.
 *
 * Throws a descriptive error if called outside of `AppProvider`, making
 * misconfigured component trees immediately obvious during development.
 *
 * @returns {{ userProfile: import('../types').UserProfile, plans: import('../types').Plan[], allNotes: import('../types').Note[], isLoading: boolean, actions: Object }}
 * @throws {Error} When used outside an `<AppProvider>`.
 */
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

/**
 * Provides global app state and business-logic mutations to the component tree.
 *
 * On mount (and whenever `isAuthenticated` changes), this provider fetches
 * the user's profile, plans, and notes in parallel via `Promise.all`. It
 * depends on both `AuthContext` (to know whether to fetch) and `ToastContext`
 * (to display error toasts on failures), so both must be ancestors in the tree.
 *
 * All `actions` that call the backend follow the same pattern:
 *   1. Call the API.
 *   2. On success, update local state optimistically.
 *   3. On failure, show a toast — callers do not need to handle errors themselves.
 *
 * @param {{ children: React.ReactNode }} props
 * @returns {JSX.Element}
 */
export const AppProvider = ({ children }) => {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const toast = useToast();
  
  const [userProfile, setUserProfile] = useState(createEmptyUserProfile());
  const [plans, setPlans] = useState([]);
  const [allNotes, setAllNotes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadInitialData = async () => {
      if (authLoading) return;
      
      setIsLoading(true);
      try {
        if (isAuthenticated) {
          const [profile, plansList, notesList] = await Promise.all([
            userProfileApi.get(),
            plansApi.list(),
            notesApi.list()
          ]);
          
          if (profile) setUserProfile(profile);
          if (plansList) setPlans(plansList);
          if (notesList) setAllNotes(notesList);
        } else {
          setUserProfile(createEmptyUserProfile());
          setPlans([]);
          setAllNotes([]);
        }
      } catch (error) {
        toast.error('加载数据失败，请刷新重试');
      } finally {
        setIsLoading(false);
      }
    };
    
    loadInitialData();
  }, [isAuthenticated, authLoading]);

  /**
   * Creates a new learning plan from an AI graph result and prepends it to
   * the local `plans` array.
   *
   * @param {string} input - The original user goal text.
   * @param {{ interpretation?: string, targetNodeId: string, nodes: import('../types').GraphNode[], edges: import('../types').GraphEdge[] }} graphResult
   * @returns {Promise<import('../types').Plan>}
   * @throws Re-throws on API failure (after showing a toast).
   */
  const createPlan = async (input, graphResult) => {
    try {
      const newPlan = await plansApi.create({
        title: graphResult.interpretation || input,
        originalInput: input,
        targetNodeId: graphResult.targetNodeId,
        nodes: graphResult.nodes,
        edges: graphResult.edges,
      });
      setPlans(prev => [newPlan, ...prev]);
      return newPlan;
    } catch (error) {
      toast.error('创建计划失败');
      throw error;
    }
  };

  /**
   * Partially updates a plan's metadata and merges the response into local state.
   *
   * @param {string} id
   * @param {Partial<import('../types').Plan>} data
   * @returns {Promise<import('../types').Plan|undefined>}
   */
  const updatePlan = async (id, data) => {
    try {
      const updated = await plansApi.update(id, data);
      setPlans(prev => prev.map(p => p.id === id ? { ...p, ...updated } : p));
      return updated;
    } catch (error) {
      toast.error('更新计划失败');
    }
  };

  /**
   * Archives a plan by setting its status to `'archived'` in local state.
   * @param {string} id
   * @returns {Promise<void>}
   */
  const archivePlan = async (id) => {
    try {
      await plansApi.archive(id);
      setPlans(prev => prev.map(p => p.id === id ? { ...p, status: 'archived' } : p));
    } catch (error) {
      toast.error('归档计划失败');
    }
  };

  /**
   * Permanently deletes a plan and removes it from local state.
   * @param {string} id
   * @returns {Promise<void>}
   */
  const deletePlan = async (id) => {
    try {
      await plansApi.delete(id);
      setPlans(prev => prev.filter(p => p.id !== id));
    } catch (error) {
      toast.error('删除计划失败');
    }
  };

  /**
   * Creates a Markdown note for a specific node and prepends it to `allNotes`.
   *
   * @param {string} planId
   * @param {string} nodeId
   * @param {string} content - Markdown text.
   * @returns {Promise<import('../types').Note|undefined>}
   */
  const addNote = async (planId, nodeId, content) => {
    try {
      const newNote = await notesApi.create(planId, nodeId, content);
      setAllNotes(prev => [newNote, ...prev]);
      return newNote;
    } catch (error) {
      toast.error('添加笔记失败');
    }
  };

  /**
   * Permanently deletes a note and removes it from `allNotes`.
   * @param {string} noteId
   * @returns {Promise<void>}
   */
  const deleteNote = async (noteId) => {
    try {
      await notesApi.delete(noteId);
      setAllNotes(prev => prev.filter(n => n.id !== noteId));
    } catch (error) {
      toast.error('删除笔记失败');
    }
  };

  /**
   * Updates a node's status inside the local `plans` state and recalculates
   * the plan's `progress` / `total` counters.
   *
   * **Local-only** — this does NOT call the API. The caller must separately
   * invoke `graphApi.updateNodeStatus` to persist the change.
   *
   * Skipped nodes are excluded from the `total` count so progress reflects
   * only the nodes the user intends to learn.
   *
   * @param {string} planId
   * @param {string} nodeId
   * @param {'unlearned'|'learned'|'skipped'} status
   */
  const updateNodeStatusInPlan = (planId, nodeId, status) => {
    setPlans(prev => prev.map(plan => {
      if (plan.id !== planId) return plan;
      const updatedNodes = (plan.nodes || []).map(n =>
        n.id === nodeId ? { ...n, status } : n
      );
      const relevant = updatedNodes.filter(n => n.status !== 'skipped');
      const learned = relevant.filter(n => n.status === 'learned').length;
      return { ...plan, nodes: updatedNodes, progress: learned, total: relevant.length };
    }));
  };

  /**
   * Updates the user's learning profile on the backend and syncs local state.
   * @param {import('../types').UserProfile} newProfile
   * @returns {Promise<void>}
   */
  const updateUserProfile = async (newProfile) => {
    try {
      const updated = await userProfileApi.update(newProfile);
      setUserProfile(updated);
    } catch (error) {
      toast.error('更新用户画像失败');
    }
  };

  const value = {
    userProfile,
    plans,
    allNotes,
    isLoading,
    actions: {
      setUserProfile: updateUserProfile,
      setPlans,
      createPlan,
      updatePlan,
      archivePlan,
      deletePlan,
      addNote,
      deleteNote,
      updateNodeStatusInPlan,
    }
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};
