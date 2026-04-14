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
  const dragFrameRef = useRef(null);
  const latestNodePositionRef = useRef(null);

  const selectedNode = useMemo(() => 
    nodes.find(n => n.id === selectedNodeId),
    [nodes, selectedNodeId]
  );

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
      setIsDragging(true);
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
    }
  }, [position]);

  const handleMouseMove = useCallback((e, containerRef) => {
    if (isDragging) {
      setPosition({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
    if (draggingNodeId && containerRef?.current) {
      const rect = containerRef.current.getBoundingClientRect();
      latestNodePositionRef.current = {
        id: draggingNodeId,
        x: (e.clientX - rect.left - position.x) / scale,
        y: (e.clientY - rect.top - position.y) / scale,
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
  }, [isDragging, dragStart, draggingNodeId, position, scale]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDraggingNodeId(null);
  }, []);

  useEffect(() => () => {
    if (dragFrameRef.current !== null) {
      cancelAnimationFrame(dragFrameRef.current);
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
