import { useEffect, useState } from "react";

const PHASE1_LINES = [
  "分析你的学习目标与深度需求...",
  "识别核心知识领域与概念边界...",
  "规划知识依赖链与学习顺序...",
];

export default function GraphGenerationLoader({
  phase = 1,
  skeletonNodeCount = 0,
  readyCount = 0,
  totalCount = 0,
  currentlyProcessing = "",
}) {
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    if (phase !== 1) return undefined;
    setVisibleLines(0);
    const timers = PHASE1_LINES.map((_, index) =>
      setTimeout(() => setVisibleLines(index + 1), index * 900),
    );
    return () => timers.forEach(clearTimeout);
  }, [phase]);

  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center overflow-hidden rounded-[28px] bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.12),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(244,247,250,0.99))] px-8 text-center">
      <div className="pointer-events-none absolute inset-0 opacity-60">
        {[
          { left: "24%", top: "34%", color: "bg-teal-400", delay: "0ms" },
          { left: "48%", top: "26%", color: "bg-blue-500", delay: "200ms" },
          { right: "28%", top: "38%", color: "bg-cyan-400", delay: "420ms" },
          { left: "34%", bottom: "30%", color: "bg-zinc-400", delay: "130ms" },
          { right: "34%", bottom: "28%", color: "bg-teal-500", delay: "300ms" },
        ].map((dot, index) => (
          <div
            key={index}
            className={`absolute h-3 w-3 animate-pulse rounded-full ${dot.color}`}
            style={{
              left: dot.left,
              top: dot.top,
              right: dot.right,
              bottom: dot.bottom,
              animationDelay: dot.delay,
            }}
          />
        ))}
      </div>

      <span className="mb-4 rounded-full border border-blue-200 bg-white/90 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-blue-600">
        {phase === 1
          ? "Curriculum Design"
          : phase === 2
            ? "Content Generation"
            : "Integration"}
      </span>

      {phase === 1 && (
        <>
          <h3 className="mb-3 text-2xl font-semibold tracking-tight text-zinc-900">
            AI 正在规划你的学习路径
          </h3>
          <div className="mb-8 w-full max-w-sm space-y-3 text-left">
            {PHASE1_LINES.map((line, index) => (
              <p
                key={line}
                className="text-sm text-zinc-500 transition-all duration-500"
                style={{
                  opacity: visibleLines > index ? 1 : 0,
                  transform:
                    visibleLines > index ? "translateY(0)" : "translateY(6px)",
                }}
              >
                {line}
              </p>
            ))}
          </div>
          <div className="h-2 w-full max-w-md overflow-hidden rounded-full bg-zinc-100">
            <div className="h-full w-1/3 animate-pulse rounded-full bg-gradient-to-r from-teal-400 via-blue-500 to-cyan-400" />
          </div>
        </>
      )}

      {phase === 2 && (
        <>
          <h3 className="mb-2 text-2xl font-semibold tracking-tight text-zinc-900">
            已规划 {skeletonNodeCount} 个知识节点
          </h3>
          <p className="mb-6 text-sm text-zinc-500">
            AI 正在为每个概念补全学习内容...
          </p>

          {currentlyProcessing && (
            <div className="mb-6 flex items-center gap-2 rounded-full border border-blue-100 bg-white/90 px-4 py-2 text-sm text-zinc-600 shadow-sm">
              <span className="h-2 w-2 animate-ping rounded-full bg-blue-400" />
              正在研究：{currentlyProcessing}
            </div>
          )}

          <div className="mb-3 flex w-full max-w-md items-center justify-between rounded-3xl border border-zinc-100 bg-white/90 px-5 py-4 shadow-sm">
            <p className="text-sm font-medium text-zinc-700">概念研究进度</p>
            <p className="text-sm font-semibold text-teal-600">
              {readyCount} / {totalCount || skeletonNodeCount || "?"}
            </p>
          </div>

          <div className="h-2 w-full max-w-md overflow-hidden rounded-full bg-zinc-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-teal-400 via-blue-500 to-cyan-400 transition-all duration-500"
              style={{
                width:
                  totalCount > 0
                    ? `${Math.max(4, (readyCount / totalCount) * 100)}%`
                    : "4%",
              }}
            />
          </div>
        </>
      )}

      {phase === 3 && (
        <>
          <h3 className="mb-3 text-2xl font-semibold tracking-tight text-zinc-900">
            正在优化知识关联...
          </h3>
          <p className="text-sm text-zinc-500">
            整合 {totalCount || skeletonNodeCount} 个节点的内容，消除重复主题。
          </p>
        </>
      )}
    </div>
  );
}
