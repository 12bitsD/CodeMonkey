/**
 * Custom hook that manages all interactive state for the concept graph canvas.
 *
 * `useGraphInteraction` owns every piece of state needed to render and
 * manipulate an interactive, pannable, zoomable graph of concept nodes:
 *
 * - **Pan** — click-drag on the canvas background to translate the viewport.
 * - **Zoom** — Ctrl/Meta + scroll wheel or trackpad pinch to scale.
 * - **Node drag** — click-hold on a node to reposition it within the canvas.
 * - **Node selection** — click a node to select it; click the background to deselect.
 * - **Status updates** — mark a node as `unlearned`, `learned`, or `skipped`.
 * - **Recommended node** — automatically computes the next best node to study.
 *
 * All callback handlers use `useCallback` so their references remain stable
 * across re-renders. This prevents unnecessary child re-renders when only
 * unrelated state changes.
 *
 * Coordinate system note: node `x`/`y` are in *canvas space* (unscaled,
 * untranslated). The viewport transform (`scale`, `position`) is applied by
 * the rendering layer via a CSS transform or SVG `viewBox`.
 *
 * @module hooks/useGraphInteraction
 */
import { useState, useCallback, useMemo } from 'react';

/**
 * Manages all pan/zoom/drag/selection state for the graph canvas.
 *
 * @param {import('../types').GraphNode[]} [initialNodes=[]] - Nodes to display at mount.
 * @param {import('../types').GraphEdge[]} [initialEdges=[]] - Edges to display at mount.
 * @param {{ recommended_node_id?: string, reason?: string }|null} [aiRecommendation=null]
 *   Optional AI recommendation object. When present, its `recommended_node_id`
 *   takes priority over the topological fallback for `recommendedNode`.
 *
 * @returns {{
 *   nodes: import('../types').GraphNode[],
 *   edges: import('../types').GraphEdge[],
 *   selectedNodeId: string|null,
 *   selectedNode: import('../types').GraphNode|undefined,
 *   recommendedNode: (import('../types').GraphNode & { recommendReason?: string })|undefined,
 *   scale: number,
 *   position: { x: number, y: number },
 *   isDragging: boolean,
 *   draggingNodeId: string|null,
 *   setNodes: Function,
 *   setEdges: Function,
 *   setSelectedNodeId: Function,
 *   setDraggingNodeId: Function,
 *   handleWheel: Function,
 *   handleMouseDown: Function,
 *   handleMouseMove: Function,
 *   handleMouseUp: Function,
 *   setNodeStatus: Function,
 *   resetView: Function,
 *   zoomIn: Function,
 *   zoomOut: Function,
 * }}
 */
export const useGraphInteraction = (initialNodes = [], initialEdges = [], aiRecommendation = null) => {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [draggingNodeId, setDraggingNodeId] = useState(null);

  /**
   * The currently selected node object, or `undefined` when nothing is selected.
   * Derived from `selectedNodeId` — always in sync with the `nodes` array.
   */
  const selectedNode = useMemo(() => 
    nodes.find(n => n.id === selectedNodeId),
    [nodes, selectedNodeId]
  );

  /**
   * The next recommended node for the user to study.
   *
   * Priority order:
   *   1. The node identified by `aiRecommendation.recommended_node_id` (when provided).
   *   2. The topologically earliest unlearned node — i.e., the first `unlearned`
   *      node whose every incoming dependency is not `unlearned` (already done
   *      or skipped), computed via a filter over the edge list.
   *
   * Returns `undefined` when all nodes are learned/skipped.
   */
  const recommendedNode = useMemo(() => {
    if (aiRecommendation?.recommended_node_id) {
      const aiNode = nodes.find(n => n.id === aiRecommendation.recommended_node_id);
      if (aiNode) return { ...aiNode, recommendReason: aiRecommendation.reason };
    }
    return nodes.find(n =>
      n.status === 'unlearned' &&
      edges
        .filter(e => e.to === n.id)
        .every(e => nodes.find(fn => fn.id === e.from)?.status !== 'unlearned')
    );
  }, [nodes, edges, aiRecommendation]);

  /**
   * Handles scroll-wheel and trackpad-pinch events on the canvas to zoom.
   *
   * Only fires on Ctrl/Meta + wheel (browser zoom gesture) or `deltaMode === 0`
   * (trackpad pixel-mode). Pure scroll without a modifier is ignored so the
   * page can still be scrolled normally on non-canvas areas.
   *
   * Zoom range is clamped to [0.5, 3].
   *
   * @param {WheelEvent} e
   */
  const handleWheel = useCallback((e) => {
    // 允许 Ctrl/Meta + 滚轮 或 双指触控板缩放
    if (e.ctrlKey || e.metaKey || e.deltaMode === 0) {
      e.preventDefault();
      // 降低缩放灵敏度，提供更平滑的体验
      const zoomSensitivity = 0.001; 
      setScale(s => Math.min(Math.max(s - e.deltaY * zoomSensitivity, 0.5), 3));
    }
  }, []);

  /**
   * Initiates a canvas pan when the user presses the mouse on the background.
   *
   * Only triggers on clicks directly on the canvas container, the SVG element,
   * or the background overlay — NOT on node elements (nodes call
   * `stopPropagation` in their own onClick handlers).
   *
   * @param {MouseEvent} e
   * @param {React.RefObject<HTMLElement>} containerRef - Ref to the outermost canvas div.
   */
  const handleMouseDown = useCallback((e, containerRef) => {
    // 检查是否点击了画布本身（包括背景 div 或 svg）
    // 排除节点点击（节点有自己的 onClick 处理，并调用 stopPropagation）
    if (
      e.target === containerRef?.current || 
      e.target.tagName === 'svg' || 
      e.target.classList.contains('absolute') // 匹配背景层
    ) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
    }
  }, [position]);

  /**
   * Updates the canvas pan position or the dragged node's coordinates on
   * every mouse-move event while a drag is active.
   *
   * Canvas pan: moves the entire viewport by tracking the delta from
   * `dragStart` (recorded in `handleMouseDown`).
   *
   * Node drag: converts the pointer's screen position to canvas space using
   * the container's bounding rect, current `position` offset, and `scale`.
   *
   * @param {MouseEvent} e
   * @param {React.RefObject<HTMLElement>} containerRef - Ref to the outermost canvas div.
   */
  const handleMouseMove = useCallback((e, containerRef) => {
    if (isDragging) {
      setPosition({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
    if (draggingNodeId && containerRef?.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setNodes(prev => prev.map(n => 
        n.id === draggingNodeId 
          ? { 
              ...n, 
              x: (e.clientX - rect.left - position.x) / scale, 
              y: (e.clientY - rect.top - position.y) / scale 
            } 
          : n
      ));
    }
  }, [isDragging, dragStart, draggingNodeId, position, scale]);

  /**
   * Ends any active canvas pan or node drag on mouse-up.
   * @param {MouseEvent} _e
   */
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDraggingNodeId(null);
  }, []);

  /**
   * Updates a node's learning status in local state.
   *
   * This is a **local-only** update — the caller is responsible for persisting
   * the change to the backend via `graphApi.updateNodeStatus`.
   *
   * @param {string} id - Node ID.
   * @param {'unlearned'|'learned'|'skipped'} status
   */
  const setNodeStatus = useCallback((id, status) => {
    setNodes(prev => prev.map(n => n.id === id ? { ...n, status } : n));
  }, []);

  /**
   * Resets the viewport to its default state (scale = 1, position = origin).
   */
  const resetView = useCallback(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  }, []);

  /**
   * Increases the zoom level by 0.1, capped at 2×.
   */
  const zoomIn = useCallback(() => {
    setScale(s => Math.min(s + 0.1, 2));
  }, []);

  /**
   * Decreases the zoom level by 0.1, floored at 0.5×.
   */
  const zoomOut = useCallback(() => {
    setScale(s => Math.max(s - 0.1, 0.5));
  }, []);

  return {
    // State
    nodes,
    edges,
    selectedNodeId,
    selectedNode,
    recommendedNode,
    scale,
    position,
    isDragging,
    draggingNodeId,
    
    // Setters
    setNodes,
    setEdges,
    setSelectedNodeId,
    setDraggingNodeId,
    
    // Handlers
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    setNodeStatus,
    resetView,
    zoomIn,
    zoomOut
  };
};

export default useGraphInteraction;
