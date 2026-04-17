import { ExternalLink } from "lucide-react";

export function ResourceList({ resources }) {
  if (!resources?.length) return null;

  return (
    <section className="space-y-3">
      <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-400">
        <ExternalLink size={12} /> 推荐资源
      </h4>
      <div className="space-y-2">
        {resources.map((resource, index) => (
          <a
            key={index}
            href={resource.url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-3 rounded-xl bg-zinc-50 p-3 transition-colors hover:bg-zinc-100"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <div className="truncate text-sm font-medium text-zinc-800">
                  {resource.name}
                </div>
                {resource.source === "web_search" && (
                  <span className="rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-medium text-teal-700">
                    联网搜索
                  </span>
                )}
              </div>
              {resource.reason && (
                <div className="mt-0.5 text-xs text-zinc-500">{resource.reason}</div>
              )}
            </div>
            <ExternalLink size={12} className="mt-1 flex-shrink-0 text-zinc-400" />
          </a>
        ))}
      </div>
    </section>
  );
}
