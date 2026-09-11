import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Maximize2, Minus, Plus, RotateCcw, X } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import {
  DIAGRAM_CANVAS_HEIGHT,
  DIAGRAM_CANVAS_WIDTH,
  DIAGRAM_NODE_HEIGHT,
  DIAGRAM_NODE_WIDTH,
  layoutDiagram,
} from './diagram/layoutDiagram';

const MIN_SCALE = 0.6;
const COMPACT_MIN_SCALE = 0.32;
const MAX_SCALE = 1.8;
const SCALE_STEP = 0.15;

const roleClasses = {
  core: 'border-teal-300 bg-teal-50 text-zinc-950 shadow-[0_12px_35px_rgba(13,148,136,0.12)]',
  support: 'border-zinc-200 bg-white text-zinc-900',
  example: 'border-amber-200 bg-amber-50/80 text-zinc-900',
  warning: 'border-rose-200 bg-rose-50/80 text-zinc-900',
};

const edgeStyle = {
  prerequisite: { dash: undefined, curve: false, both: false },
  sequence: { dash: undefined, curve: false, both: false },
  causes: { dash: undefined, curve: true, both: false },
  contains: { dash: undefined, curve: false, both: false },
  contrasts: { dash: '8 6', curve: true, both: true },
  supports: { dash: undefined, curve: false, both: false },
  feedback: { dash: undefined, curve: true, both: true },
  related: { dash: '5 6', curve: false, both: false },
};

const clampScale = (value, minimum = MIN_SCALE) => (
  Math.min(MAX_SCALE, Math.max(minimum, Number(value.toFixed(2))))
);

function edgeAnchors(from, to) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (dx === 0 && dy === 0) return { from, to };
  const boundaryRatio = 1 / Math.max(
    Math.abs(dx) / (DIAGRAM_NODE_WIDTH / 2),
    Math.abs(dy) / (DIAGRAM_NODE_HEIGHT / 2),
  );
  const insetX = dx * boundaryRatio;
  const insetY = dy * boundaryRatio;
  return {
    from: { x: from.x + insetX, y: from.y + insetY },
    to: { x: to.x - insetX, y: to.y - insetY },
  };
}

function edgePath(from, to, style) {
  if (style.curve) {
    const bend = Math.max(55, Math.abs(to.x - from.x) * 0.22);
    return `M ${from.x} ${from.y} C ${from.x + bend} ${from.y - 50}, ${to.x - bend} ${to.y - 50}, ${to.x} ${to.y}`;
  }
  if (Math.abs(from.y - to.y) > 100) {
    const middleY = (from.y + to.y) / 2;
    return `M ${from.x} ${from.y} L ${from.x} ${middleY} L ${to.x} ${middleY} L ${to.x} ${to.y}`;
  }
  return `M ${from.x} ${from.y} L ${to.x} ${to.y}`;
}

function isUsableSpec(spec) {
  if (!spec || spec.version !== 1 || !Array.isArray(spec.nodes) || !Array.isArray(spec.edges)) return false;
  if (spec.nodes.length < 2 || spec.nodes.length > 8 || spec.edges.length > 12) return false;
  const ids = new Set(spec.nodes.map(node => node.id));
  return ids.size === spec.nodes.length
    && spec.edges.every(edge => ids.has(edge.source) && ids.has(edge.target));
}

export default function TeachingDiagram({ spec, compact = false }) {
  const { t } = useLanguage();
  const markerId = useId().replaceAll(':', '');
  const viewportRef = useRef(null);
  const dragRef = useRef(null);
  const pointersRef = useRef(new Map());
  const nodeRefs = useRef(new Map());
  const [scale, setScale] = useState(compact ? COMPACT_MIN_SCALE : 1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [selectedId, setSelectedId] = useState(null);

  const positions = useMemo(() => layoutDiagram(spec), [spec]);
  const positionById = useMemo(
    () => Object.fromEntries(positions.map(position => [position.id, position])),
    [positions],
  );
  const selectedNode = spec?.nodes?.find(node => node.id === selectedId) || null;

  const closeDetails = () => {
    nodeRefs.current.get(selectedId)?.focus();
    setSelectedId(null);
  };

  useEffect(() => {
    if (!selectedId) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        nodeRefs.current.get(selectedId)?.focus();
        setSelectedId(null);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedId]);

  if (!isUsableSpec(spec)) {
    return (
      <div className="my-3 rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-500">
        {t('deep.diagramFailed')}
      </div>
    );
  }

  const minimumScale = compact ? COMPACT_MIN_SCALE : MIN_SCALE;
  const updateScale = next => setScale(current => clampScale(
    typeof next === 'function' ? next(current) : next,
    minimumScale,
  ));

  const fitDiagram = () => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const next = Math.min(
      (viewport.clientWidth - 24) / DIAGRAM_CANVAS_WIDTH,
      (viewport.clientHeight - 24) / DIAGRAM_CANVAS_HEIGHT,
      1,
    );
    setOffset({ x: 0, y: 0 });
    updateScale(next || 1);
  };

  const resetDiagram = () => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  };

  const startDrag = (event) => {
    if (event.button !== 0) return;
    pointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    event.currentTarget.setPointerCapture?.(event.pointerId);
    const points = [...pointersRef.current.values()];
    if (points.length >= 2) {
      dragRef.current = {
        kind: 'pinch',
        distance: Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y),
        scale,
      };
      return;
    }
    dragRef.current = {
      kind: 'pan',
      x: event.clientX,
      y: event.clientY,
      origin: offset,
    };
  };

  const moveDrag = (event) => {
    if (pointersRef.current.has(event.pointerId)) {
      pointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    }
    const drag = dragRef.current;
    if (!drag) return;
    const points = [...pointersRef.current.values()];
    if (drag.kind === 'pinch' && points.length >= 2 && drag.distance > 0) {
      const distance = Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y);
      setScale(clampScale(drag.scale * (distance / drag.distance), minimumScale));
      return;
    }
    if (drag.kind !== 'pan') return;
    setOffset({
      x: drag.origin.x + event.clientX - drag.x,
      y: drag.origin.y + event.clientY - drag.y,
    });
  };

  const stopDrag = (event) => {
    pointersRef.current.delete(event.pointerId);
    const remaining = [...pointersRef.current.values()];
    dragRef.current = remaining.length === 1
      ? { kind: 'pan', x: remaining[0].x, y: remaining[0].y, origin: offset }
      : null;
  };

  return (
    <section className="my-3 overflow-hidden rounded-2xl border border-zinc-200 bg-[#fbfbfa] shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-zinc-200/80 px-4 py-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
            {t('deep.diagram.interactive')}
          </p>
          <h3 className="truncate text-sm font-semibold text-zinc-900">{spec.title}</h3>
        </div>
        <div className="flex shrink-0 items-center gap-1 rounded-full border border-zinc-200 bg-white p-1 shadow-sm">
          <button type="button" aria-label={t('deep.diagram.zoomOut')} onClick={() => updateScale(value => value - SCALE_STEP)} className="rounded-full p-1.5 text-zinc-500 hover:bg-zinc-100"><Minus size={14} /></button>
          <span className="w-10 text-center text-[10px] tabular-nums text-zinc-500">{Math.round(scale * 100)}%</span>
          <button type="button" aria-label={t('deep.diagram.zoomIn')} onClick={() => updateScale(value => value + SCALE_STEP)} className="rounded-full p-1.5 text-zinc-500 hover:bg-zinc-100"><Plus size={14} /></button>
          <button type="button" aria-label={t('deep.diagram.fit')} onClick={fitDiagram} className="rounded-full p-1.5 text-zinc-500 hover:bg-zinc-100"><Maximize2 size={14} /></button>
          <button type="button" aria-label={t('deep.diagram.reset')} onClick={resetDiagram} className="rounded-full p-1.5 text-zinc-500 hover:bg-zinc-100"><RotateCcw size={14} /></button>
        </div>
      </div>

      <div
        ref={viewportRef}
        data-testid="teaching-diagram-viewport"
        className={`relative cursor-grab overflow-hidden bg-[radial-gradient(circle_at_center,_rgba(24,24,27,0.05)_1px,_transparent_1px)] [background-size:22px_22px] active:cursor-grabbing ${compact ? 'h-[280px]' : 'h-[430px]'}`}
        style={{ touchAction: 'none' }}
        onPointerDown={startDrag}
        onPointerMove={moveDrag}
        onPointerUp={stopDrag}
        onPointerCancel={stopDrag}
        onWheel={(event) => {
          if (!event.ctrlKey && !event.metaKey) return;
          event.preventDefault();
          updateScale(value => value + (event.deltaY < 0 ? SCALE_STEP : -SCALE_STEP));
        }}
      >
        <div
          data-testid="teaching-diagram-canvas"
          className="absolute left-1/2 top-1/2"
          style={{
            width: DIAGRAM_CANVAS_WIDTH,
            height: DIAGRAM_CANVAS_HEIGHT,
            transform: `translate(calc(-50% + ${offset.x}px), calc(-50% + ${offset.y}px)) scale(${scale})`,
            transformOrigin: 'center',
          }}
        >
          <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full overflow-visible">
            <defs>
              <marker id={`${markerId}-end`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#a1a1aa" />
              </marker>
            </defs>
            {spec.edges.map((edge, index) => {
              const from = positionById[edge.source];
              const to = positionById[edge.target];
              const style = edgeStyle[edge.relation] || edgeStyle.related;
              if (!from || !to) return null;
              const anchors = edgeAnchors(from, to);
              const labelX = (from.x + to.x) / 2;
              const labelY = (from.y + to.y) / 2 - 9;
              return (
                <g key={`${edge.source}-${edge.target}-${index}`}>
                  <path
                    d={edgePath(anchors.from, anchors.to, style)}
                    fill="none"
                    stroke="#a1a1aa"
                    strokeWidth="2"
                    strokeDasharray={style.dash}
                    markerStart={style.both ? `url(#${markerId}-end)` : undefined}
                    markerEnd={`url(#${markerId}-end)`}
                  />
                  {edge.label && (
                    <g transform={`translate(${labelX} ${labelY})`}>
                      <rect x="-42" y="-10" width="84" height="20" rx="10" fill="#fbfbfa" />
                      <text textAnchor="middle" dominantBaseline="middle" className="fill-zinc-500 text-[11px]">{edge.label}</text>
                    </g>
                  )}
                </g>
              );
            })}
          </svg>

          {spec.nodes.map(node => {
            const position = positionById[node.id];
            return (
              <button
                key={node.id}
                ref={element => {
                  if (element) nodeRefs.current.set(node.id, element);
                  else nodeRefs.current.delete(node.id);
                }}
                type="button"
                aria-label={`${node.title}：${node.summary}`}
                onPointerDown={event => event.stopPropagation()}
                onClick={() => setSelectedId(node.id)}
                className={`absolute flex flex-col items-start justify-center rounded-2xl border px-4 py-3 text-left transition duration-200 hover:-translate-y-1 hover:shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 ${roleClasses[node.role] || roleClasses.support}`}
                style={{
                  width: DIAGRAM_NODE_WIDTH,
                  height: DIAGRAM_NODE_HEIGHT,
                  left: position.x - DIAGRAM_NODE_WIDTH / 2,
                  top: position.y - DIAGRAM_NODE_HEIGHT / 2,
                }}
              >
                <span className="mb-1 text-sm font-semibold leading-tight">{node.title}</span>
                <span className="line-clamp-2 text-[11px] leading-4 text-zinc-500">{node.summary}</span>
              </button>
            );
          })}
        </div>

        {selectedNode && (
          <div
            role="dialog"
            aria-label={selectedNode.title}
            className="absolute bottom-3 right-3 z-20 max-h-[calc(100%-24px)] w-[min(330px,calc(100%-24px))] overflow-auto rounded-2xl border border-zinc-200 bg-white/95 p-4 shadow-2xl backdrop-blur"
          >
            <button type="button" aria-label={t('deep.diagram.closeDetails')} onClick={closeDetails} className="absolute right-3 top-3 rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"><X size={16} /></button>
            <p className="pr-8 text-base font-semibold text-zinc-950">{selectedNode.title}</p>
            <p className="mt-1 text-sm leading-6 text-zinc-600">{selectedNode.summary}</p>
            {selectedNode.details?.key_points?.length > 0 && (
              <div className="mt-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-600">{t('deep.diagram.keyPoints')}</p>
                <ul className="mt-2 space-y-1.5 text-sm text-zinc-700">
                  {selectedNode.details.key_points.map(point => <li key={point} className="flex gap-2"><span className="text-teal-500">•</span><span>{point}</span></li>)}
                </ul>
              </div>
            )}
            {selectedNode.details?.example && <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-sm leading-5 text-zinc-700"><span className="font-medium">{t('deep.diagram.example')}：</span>{selectedNode.details.example}</p>}
            {selectedNode.details?.misconception && <p className="mt-2 rounded-xl bg-rose-50 px-3 py-2 text-sm leading-5 text-zinc-700"><span className="font-medium">{t('deep.diagram.misconception')}：</span>{selectedNode.details.misconception}</p>}
          </div>
        )}
      </div>
    </section>
  );
}
