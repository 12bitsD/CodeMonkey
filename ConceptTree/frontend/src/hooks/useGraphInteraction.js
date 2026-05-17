import { useState, useCallback, useMemo, useRef, useEffect } from 'react';

export const useGraphInteraction = (initialNodes = [], initialEdges = [], aiRecommendation = null) => {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [draggingNodeId, setDraggingNodeId] = useState(null);
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef(dragStart);
  const dragFrameRef = useRef(null);
  const panFrameRef = useRef(null);
  const latestCanvasPositionRef = useRef(null);
  const latestNodePositionRef = useRef(null);
  const positionRef = useRef(position);

  useEffect(() => {
    positionRef.current = position;
  }, [position]);

  const nodeMap = useMemo(
    () => new Map(nodes.map((node) => [node.id, node])),
    [nodes],
  );

  const prerequisiteMap = useMemo(() => {
    const map = new Map();
    for (const edge of edges) {
      if (!map.has(edge.to)) {
        map.set(edge.to, []);
      }
      map.get(edge.to).push(edge.from);
    }
    return map;
  }, [edges]);

  const selectedNode = useMemo(
    () => nodeMap.get(selectedNodeId),
    [nodeMap, selectedNodeId],
  );

  const recommendedNode = useMemo(() => {
    if (aiRecommendation?.recommended_node_id) {
      const aiNode = nodeMap.get(aiRecommendation.recommended_node_id);
      if (aiNode) return { ...aiNode, recommendReason: aiRecommendation.reason };
    }
    return nodes.find((node) => {
      if (node.status !== 'unlearned') return false;
      const prerequisiteIds = prerequisiteMap.get(node.id) || [];
      return prerequisiteIds.every((id) => nodeMap.get(id)?.status !== 'unlearned');
    });
  }, [nodes, nodeMap, prerequisiteMap, aiRecommendation]);

  const handleWheel = useCallback((e) => {
    // 允许 Ctrl/Meta + 滚轮 或 双指触控板缩放
    if (e.ctrlKey || e.metaKey || e.deltaMode === 0) {
      e.preventDefault();
      // 降低缩放灵敏度，提供更平滑的体验
      const zoomSensitivity = 0.001; 
      setScale(s => Math.min(Math.max(s - e.deltaY * zoomSensitivity, 0.5), 3));
    }
  }, []);

  const handleMouseDown = useCallback((e, containerRef) => {
    // 检查是否点击了画布本身（包括背景 div 或 svg）
    // 排除节点点击（节点有自己的 onClick 处理，并调用 stopPropagation）
    if (
      e.target === containerRef?.current || 
      e.target.tagName === 'svg' || 
      e.target.classList.contains('absolute') // 匹配背景层
    ) {
      const currentPosition = positionRef.current;
      const nextDragStart = {
        x: e.clientX - currentPosition.x,
        y: e.clientY - currentPosition.y,
      };
      isDraggingRef.current = true;
      dragStartRef.current = nextDragStart;
      latestCanvasPositionRef.current = currentPosition;
      setIsDragging(true);
      setDragStart(nextDragStart);
    }
  }, []);

  const handleMouseMove = useCallback((e, containerRef) => {
    if (isDraggingRef.current) {
      const currentDragStart = dragStartRef.current;
      latestCanvasPositionRef.current = {
        x: e.clientX - currentDragStart.x,
        y: e.clientY - currentDragStart.y,
      };
      if (panFrameRef.current === null) {
        panFrameRef.current = requestAnimationFrame(() => {
          const next = latestCanvasPositionRef.current;
          panFrameRef.current = null;
          if (!next) return;
          setPosition(next);
        });
      }
    }
    if (draggingNodeId && containerRef?.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const currentPosition = positionRef.current;
      latestNodePositionRef.current = {
        id: draggingNodeId,
        x: (e.clientX - rect.left - currentPosition.x) / scale,
        y: (e.clientY - rect.top - currentPosition.y) / scale,
      };

      if (dragFrameRef.current === null) {
        dragFrameRef.current = requestAnimationFrame(() => {
          const next = latestNodePositionRef.current;
          dragFrameRef.current = null;
          if (!next) return;

          setNodes(prev => prev.map(n =>
            n.id === next.id
              ? {
                  ...n,
                  x: next.x,
                  y: next.y,
                }
              : n
          ));
        });
      }
    }
  }, [draggingNodeId, scale]);

  const handleMouseUp = useCallback(() => {
    if (panFrameRef.current !== null) {
      cancelAnimationFrame(panFrameRef.current);
      panFrameRef.current = null;
    }
    if (latestCanvasPositionRef.current) {
      positionRef.current = latestCanvasPositionRef.current;
      setPosition(latestCanvasPositionRef.current);
    }
    if (dragFrameRef.current !== null) {
      cancelAnimationFrame(dragFrameRef.current);
      dragFrameRef.current = null;
    }
    if (latestNodePositionRef.current) {
      const next = latestNodePositionRef.current;
      setNodes(prev => prev.map(n =>
        n.id === next.id
          ? {
              ...n,
              x: next.x,
              y: next.y,
            }
          : n
      ));
    }
    isDraggingRef.current = false;
    latestCanvasPositionRef.current = null;
    latestNodePositionRef.current = null;
    setIsDragging(false);
    setDraggingNodeId(null);
  }, []);

  useEffect(() => () => {
    if (dragFrameRef.current !== null) {
      cancelAnimationFrame(dragFrameRef.current);
    }
    if (panFrameRef.current !== null) {
      cancelAnimationFrame(panFrameRef.current);
    }
  }, []);

  const setNodeStatus = useCallback((id, status) => {
    setNodes(prev => prev.map(n => n.id === id ? { ...n, status } : n));
  }, []);

  const resetView = useCallback(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  }, []);

  const zoomIn = useCallback(() => {
    setScale(s => Math.min(s + 0.1, 2));
  }, []);

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
    setPosition,
    
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
