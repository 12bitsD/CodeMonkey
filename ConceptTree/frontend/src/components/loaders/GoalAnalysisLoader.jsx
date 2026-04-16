const ANALYSIS_LOADING_TEXTS = [
  "解析概念边界与学习意图",
  "识别你的背景与目标重心",
  "准备更清晰的学习澄清问题",
];

export default function GoalAnalysisLoader({ step = 0 }) {
  const message = ANALYSIS_LOADING_TEXTS[step % ANALYSIS_LOADING_TEXTS.length];

  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center overflow-hidden rounded-[28px] bg-[radial-gradient(circle_at_top,rgba(94,234,212,0.16),transparent_38%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] px-8 text-center">
      <div className="pointer-events-none absolute inset-0 opacity-70">
        <div className="absolute left-1/2 top-[24%] h-32 w-32 -translate-x-1/2 rounded-full bg-teal-100/70 blur-2xl" />
        <div className="absolute left-[32%] top-[34%] h-16 w-16 rounded-full border border-teal-200/70 animate-pulse" />
        <div className="absolute right-[34%] top-[36%] h-10 w-10 rounded-full border border-cyan-200/80 animate-pulse [animation-delay:180ms]" />
        <div className="absolute left-[42%] top-[48%] h-24 w-24 rounded-full border border-zinc-200/80 animate-pulse [animation-delay:320ms]" />
      </div>

      <div className="relative mb-8 flex h-24 w-24 items-center justify-center">
        <div className="absolute inset-0 rounded-full border border-teal-200/80 animate-ping" />
        <div className="absolute inset-3 rounded-full border border-teal-300/70" />
        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-teal-400 to-cyan-500 shadow-[0_0_30px_rgba(45,212,191,0.35)]" />
      </div>

      <span className="mb-4 rounded-full border border-teal-200 bg-white/80 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-teal-600">
        Goal Analysis
      </span>
      <h3 className="mb-3 text-2xl font-semibold tracking-tight text-zinc-900">
        AI 正在理解你的学习目标
      </h3>
      <p className="mb-6 text-sm text-zinc-500">{message}</p>

      <div className="w-full max-w-sm space-y-3">
        {[0, 1, 2].map((line) => (
          <div
            key={line}
            className="h-2.5 rounded-full bg-gradient-to-r from-teal-100 via-zinc-100 to-cyan-100 animate-pulse"
            style={{ width: `${100 - line * 12}%`, animationDelay: `${line * 140}ms` }}
          />
        ))}
      </div>
    </div>
  );
}
