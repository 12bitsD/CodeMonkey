import { AlertTriangle, CheckCircle2, ChevronRight, Circle, XCircle } from 'lucide-react';
import PinnedImages from './PinnedImages';

const STATUS_ICON = {
  done: <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />,
  current: <ChevronRight className="w-4 h-4 text-blue-500 shrink-0" />,
  failed: <XCircle className="w-4 h-4 text-red-500 shrink-0" />,
  skipped: <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />,
  pending: <Circle className="w-4 h-4 text-zinc-300 shrink-0" />,
};

const STATUS_CLASS = {
  current: 'bg-blue-50 text-blue-700',
  done: 'text-zinc-700',
  failed: 'bg-red-50 text-red-700',
  skipped: 'bg-amber-50 text-amber-700',
  pending: 'text-zinc-700',
};

export default function ConceptProgress({ whatList, conceptsStatus, weakPoints, pinnedImages = [], onUnpinImage }) {
  const total = whatList.length;
  const completed = Object.values(conceptsStatus)
    .filter(s => ['done', 'failed', 'skipped'].includes(s)).length;

  return (
    <div className="p-4 flex flex-col gap-4">
      <div>
        <div className="flex justify-between text-xs text-zinc-500 mb-1">
          <span>进度</span>
          <span>{completed} / {total}</span>
        </div>
        <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: total ? `${(completed / total) * 100}%` : '0%' }}
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">概念列表</p>
        {whatList.map((concept, i) => {
          const status = conceptsStatus[String(i)] || 'pending';
          return (
            <div
              key={i}
              className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm ${STATUS_CLASS[status] || STATUS_CLASS.pending}`}
            >
              {STATUS_ICON[status] || STATUS_ICON.pending}
              <span className="truncate">{concept}</span>
            </div>
          );
        })}
      </div>

      {weakPoints.length > 0 && (
        <div>
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">弱点追踪</p>
          <div className="flex flex-col gap-1">
            {weakPoints.map((w, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-yellow-700 bg-yellow-50 px-2 py-1 rounded">
                <AlertTriangle className="w-3 h-3 shrink-0" />
                <span>{w}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <PinnedImages pinned={pinnedImages} onUnpin={onUnpinImage} />
    </div>
  );
}
