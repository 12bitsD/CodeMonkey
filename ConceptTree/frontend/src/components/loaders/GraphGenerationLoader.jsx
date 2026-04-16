import { LOADING_TEXTS } from "../../constants";

export default function GraphGenerationLoader({ loadingStep = 0, streamProgress = null }) {
  const progressLabel = streamProgress
    ? `已生成 ${streamProgress.received}/${streamProgress.total || "?"} 个节点`
    : LOADING_TEXTS[loadingStep % LOADING_TEXTS.length];

  const completionRatio = streamProgress?.total
    ? Math.max(0.08, Math.min(1, streamProgress.received / streamProgress.total))
    : Math.min(0.92, 0.18 + loadingStep * 0.14);

  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center overflow-hidden rounded-[28px] bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.12),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(244,247,250,0.99))] px-8 text-center">
      <div className="pointer-events-none absolute inset-0 opacity-80">
        <div className="absolute left-[24%] top-[34%] h-3 w-3 rounded-full bg-teal-400 animate-pulse" />
        <div className="absolute left-[48%] top-[26%] h-3.5 w-3.5 rounded-full bg-blue-500 animate-pulse [animation-delay:200ms]" />
        <div className="absolute right-[28%] top-[38%] h-3 w-3 rounded-full bg-cyan-400 animate-pulse [animation-delay:420ms]" />
        <div className="absolute left-[34%] bottom-[30%] h-3 w-3 rounded-full bg-zinc-400 animate-pulse [animation-delay:130ms]" />
        <div className="absolute right-[34%] bottom-[28%] h-3 w-3 rounded-full bg-teal-500 animate-pulse [animation-delay:300ms]" />

        <div className="absolute left-[25%] top-[35%] h-px w-[22%] origin-left bg-gradient-to-r from-teal-300 to-blue-300 opacity-80" />
        <div className="absolute left-[50%] top-[27%] h-[20%] w-px bg-gradient-to-b from-blue-300 to-cyan-300 opacity-70" />
        <div className="absolute right-[29%] top-[39%] h-px w-[20%] origin-right bg-gradient-to-l from-cyan-300 to-zinc-300 opacity-70" />
        <div className="absolute left-[35%] bottom-[31%] h-[16%] w-px bg-gradient-to-b from-zinc-300 to-teal-300 opacity-65" />
      </div>

      <span className="mb-4 rounded-full border border-blue-200 bg-white/90 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-blue-600">
        Graph Generation
      </span>
      <h3 className="mb-3 text-2xl font-semibold tracking-tight text-zinc-900">
        正在为你生成学习图谱
      </h3>
      <p className="mb-8 max-w-md text-sm text-zinc-500">
        从目标拆解到知识节点排序，AI 正在逐步构建一条更清晰的学习路径。
      </p>

      <div className="mb-6 flex w-full max-w-md items-center justify-between rounded-3xl border border-zinc-100 bg-white/90 px-5 py-4 shadow-[0_12px_30px_rgba(15,23,42,0.06)]">
        <div className="text-left">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-400">
            Current Step
          </p>
          <p className="mt-1 text-sm font-medium text-zinc-700">{progressLabel}</p>
        </div>
        <div className="rounded-2xl bg-zinc-50 px-3 py-2 text-right">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
            Status
          </p>
          <p className="mt-1 text-sm font-semibold text-teal-600">
            {Math.round(completionRatio * 100)}%
          </p>
        </div>
      </div>

      <div className="w-full max-w-md">
        <div className="mb-3 h-2 overflow-hidden rounded-full bg-zinc-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-teal-400 via-blue-500 to-cyan-400 transition-all duration-500"
            style={{ width: `${completionRatio * 100}%` }}
          />
        </div>
        <div className="flex justify-between text-[11px] text-zinc-400">
          <span>构建核心概念</span>
          <span>排序依赖关系</span>
          <span>组织学习路径</span>
        </div>
      </div>
    </div>
  );
}
