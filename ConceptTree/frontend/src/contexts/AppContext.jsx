import React, { createContext, useContext, useMemo } from 'react';
import { GraphProvider, useGraphContext } from './GraphContext';
import { NoteProvider, useNoteContext } from './NoteContext';
import { PlanProvider, usePlanContext } from './PlanContext';
import { getApiErrorMessage, isRecoverableApiError } from '../utils/apiErrorMessages';

const AppContext = createContext(null);

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

const AppContextBridge = ({ children }) => {
  const plan = usePlanContext();
  const note = useNoteContext();
  const graph = useGraphContext();

  const value = useMemo(
    () => {
      const loadErrors = [plan.loadError, note.loadError].filter(Boolean);
      const recoverableError = loadErrors.find(isRecoverableApiError);

      return {
        userProfile: plan.userProfile,
        plans: plan.plans,
        allNotes: note.allNotes,
        graphSnapshots: graph.graphsByPlanId,
        isLoading: plan.isLoading || note.isLoading,
        dataSyncStatus: {
          degraded: Boolean(recoverableError),
          message: recoverableError ? getApiErrorMessage(recoverableError) : '',
          code: recoverableError?.code || null,
        },
        actions: {
          ...plan.actions,
          ...note.actions,
          ...graph.actions,
        },
      };
    },
    [
      graph.actions,
      graph.graphsByPlanId,
      note.actions,
      note.allNotes,
      note.isLoading,
      note.loadError,
      plan.actions,
      plan.isLoading,
      plan.loadError,
      plan.plans,
      plan.userProfile,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const AppProvider = ({ children }) => (
  <PlanProvider>
    <NoteProvider>
      <GraphProvider>
        <AppContextBridge>{children}</AppContextBridge>
      </GraphProvider>
    </NoteProvider>
  </PlanProvider>
);
