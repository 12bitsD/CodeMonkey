import React, { createContext, useContext, useMemo, useState } from 'react';

const GraphContext = createContext(null);
const GRAPH_CACHE_KEY = 'concept_tree_graph_cache';

const normalizeGraphSnapshot = (graph) => ({
  title: graph?.title || null,
  nodes: Array.isArray(graph?.nodes) ? graph.nodes : [],
  edges: Array.isArray(graph?.edges) ? graph.edges : [],
  updatedAt: Date.now(),
});

const readGraphCache = () => {
  try {
    const raw = window.localStorage.getItem(GRAPH_CACHE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
};

const writeGraphCache = (graphsByPlanId) => {
  try {
    window.localStorage.setItem(GRAPH_CACHE_KEY, JSON.stringify(graphsByPlanId || {}));
  } catch {
    // localStorage may be unavailable; keep in-memory graph snapshots.
  }
};

export const useGraphContext = () => {
  const context = useContext(GraphContext);
  if (!context) {
    throw new Error('useGraphContext must be used within a GraphProvider');
  }
  return context;
};

export const GraphProvider = ({ children }) => {
  const [graphsByPlanId, setGraphsByPlanId] = useState(() => readGraphCache());

  const actions = useMemo(
    () => ({
      setGraph(planId, graph) {
        if (!planId) return;
        setGraphsByPlanId((prev) => {
          const next = {
            ...prev,
            [planId]: normalizeGraphSnapshot(graph),
          };
          writeGraphCache(next);
          return next;
        });
      },
      clearGraph(planId) {
        if (!planId) return;
        setGraphsByPlanId((prev) => {
          const next = { ...prev };
          delete next[planId];
          writeGraphCache(next);
          return next;
        });
      },
      updateGraphNodes(planId, updater) {
        if (!planId) return;
        setGraphsByPlanId((prev) => {
          const current = prev[planId] || normalizeGraphSnapshot({});
          const nextNodes = typeof updater === 'function' ? updater(current.nodes) : updater;
          const next = {
            ...prev,
            [planId]: {
              ...current,
              nodes: Array.isArray(nextNodes) ? nextNodes : current.nodes,
              updatedAt: Date.now(),
            },
          };
          writeGraphCache(next);
          return next;
        });
      },
      updateGraphEdges(planId, updater) {
        if (!planId) return;
        setGraphsByPlanId((prev) => {
          const current = prev[planId] || normalizeGraphSnapshot({});
          const nextEdges = typeof updater === 'function' ? updater(current.edges) : updater;
          const next = {
            ...prev,
            [planId]: {
              ...current,
              edges: Array.isArray(nextEdges) ? nextEdges : current.edges,
              updatedAt: Date.now(),
            },
          };
          writeGraphCache(next);
          return next;
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
