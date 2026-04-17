import MarkdownContent from "../common/MarkdownContent";

const SEARCH_STATUS_LABELS = {
  searching: "正在联网搜索资料...",
  fallback: "未获取到外部资料，已切换为普通回答。",
  done: "参考资料已整理完成。",
};

export default function ChatMarkdownMessage({
  content,
  isPending = false,
  sources = [],
  searchStatus = null,
}) {
  const showStatus =
    searchStatus && SEARCH_STATUS_LABELS[searchStatus] && searchStatus !== "done";

  return (
    <div className="max-w-[88%] rounded-[22px] rounded-bl-sm border border-teal-100/80 bg-gradient-to-br from-white via-teal-50/70 to-cyan-50/80 px-4 py-3 text-zinc-700 shadow-[0_10px_30px_rgba(20,184,166,0.08)]">
      <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-teal-500">
        <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
        AI 回复
      </div>
      {showStatus && (
        <div className="mb-3 rounded-2xl border border-teal-100 bg-white/80 px-3 py-2 text-[11px] text-teal-700">
          {SEARCH_STATUS_LABELS[searchStatus]}
        </div>
      )}
      {isPending ? (
        <div className="space-y-2">
          <div className="h-3 w-3/4 animate-pulse rounded-full bg-teal-100" />
          <div className="h-3 w-full animate-pulse rounded-full bg-zinc-100" />
          <div className="h-3 w-4/5 animate-pulse rounded-full bg-zinc-100" />
        </div>
      ) : (
        <MarkdownContent content={content} />
      )}
      {sources.length > 0 && (
        <div className="mt-4 space-y-2 border-t border-teal-100/80 pt-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
            参考来源
          </div>
          {sources.map((source, index) => (
            <a
              key={`${source.url}-${index}`}
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="block rounded-2xl border border-zinc-100 bg-white/85 px-3 py-2 transition-colors hover:border-teal-200 hover:bg-white"
            >
              <div className="text-xs font-medium text-zinc-800">{source.title}</div>
              <div className="mt-1 text-[11px] text-zinc-400">{source.source}</div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
