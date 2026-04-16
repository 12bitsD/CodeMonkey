import React, { createContext, useContext, useMemo, useState } from 'react';

const GraphContext = createContext(null);

const normalizeGraphSnapshot = (graph) => ({
  title: graph?.title || null,
  nodes: Array.isArray(graph?.nodes) ? graph.nodes : [],
  edges: Array.isArray(graph?.edges) ? graph.edges : [],
  updatedAt: Date.now(),
});

export const useGraphContext = () => {
  const context = useContext(GraphContext);
  if (!context) {
    throw new Error('useGraphContext must be used within a GraphProvider');
  }
  return context;
};

export const GraphProvider = ({ children }) => {
  const [graphsByPlanId, setGraphsByPlanId] = useState({});

  const actions = useMemo(
    () => ({
      setGraph(planId, graph) {
        if (!planId) return;
        setGraphsByPlanId((prev) => ({
          ...prev,
          [planId]: normalizeGraphSnapshot(graph),
        }));
      },
      clearGraph(planId) {
        if (!planId) return;
        setGraphsByPlanId((prev) => {
          const next = { ...prev };
          delete next[planId];
          return next;
        });
      },
      updateGraphNodes(planId, updater) {
        if (!planId) return;
        setGraphsByPlanId((prev) => {
          const current = prev[planId] || normalizeGraphSnapshot({});
          const nextNodes = typeof updater === 'function' ? updater(current.nodes) : updater;
          return {
            ...prev,
            [planId]: {
              ...current,
              nodes: Array.isArray(nextNodes) ? nextNodes : current.nodes,
              updatedAt: Date.now(),
            },
          };
        });
      },
      updateGraphEdges(planId, updater) {
        if (!planId) return;
        setGraphsByPlanId((prev) => {
          const current = prev[planId] || normalizeGraphSnapshot({});
          const nextEdges = typeof updater === 'function' ? updater(current.edges) : updater;
          return {
            ...prev,
            [planId]: {
              ...current,
              edges: Array.isArray(nextEdges) ? nextEdges : current.edges,
              updatedAt: Date.now(),
            },
          };
        });
      },
    }),
    [],
  );

  const value = useMemo(
    () => ({
      graphsByPlanId,
      actions,
    }),
    [actions, graphsByPlanId],
  );

  return <GraphContext.Provider value={value}>{children}</GraphContext.Provider>;
};
