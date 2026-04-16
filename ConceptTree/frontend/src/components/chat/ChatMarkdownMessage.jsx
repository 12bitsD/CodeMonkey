import MarkdownContent from "../common/MarkdownContent";

export default function ChatMarkdownMessage({ content, isPending = false }) {
  return (
    <div className="max-w-[88%] rounded-[22px] rounded-bl-sm border border-teal-100/80 bg-gradient-to-br from-white via-teal-50/70 to-cyan-50/80 px-4 py-3 text-zinc-700 shadow-[0_10px_30px_rgba(20,184,166,0.08)]">
      <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-teal-500">
        <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
        AI Reply
      </div>
      {isPending ? (
        <div className="space-y-2">
          <div className="h-3 w-3/4 animate-pulse rounded-full bg-teal-100" />
          <div className="h-3 w-full animate-pulse rounded-full bg-zinc-100" />
          <div className="h-3 w-4/5 animate-pulse rounded-full bg-zinc-100" />
        </div>
      ) : (
        <MarkdownContent content={content} />
      )}
    </div>
  );
}
