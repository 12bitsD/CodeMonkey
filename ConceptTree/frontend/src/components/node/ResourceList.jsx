import { ExternalLink } from 'lucide-react';

export function ResourceList({ resources }) {
  if (!resources?.length) return null;
  return (
    <section className="space-y-3">
      <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
        <ExternalLink size={12} /> 推荐资源
      </h4>
      <div className="space-y-2">
        {resources.map((r, i) => (
          <a
            key={i}
            href={r.url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-3 p-3 bg-zinc-50 rounded-xl hover:bg-zinc-100 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-zinc-800 truncate">{r.name}</div>
              {r.reason && <div className="text-xs text-zinc-500 mt-0.5">{r.reason}</div>}
            </div>
            <ExternalLink size={12} className="text-zinc-400 flex-shrink-0 mt-1" />
          </a>
        ))}
      </div>
    </section>
  );
}
