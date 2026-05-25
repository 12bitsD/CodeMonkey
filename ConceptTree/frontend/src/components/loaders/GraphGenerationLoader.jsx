export default function GraphGenerationLoader({
  readyCount = 0,
  totalCount = 0,
}) {
  const progress = totalCount > 0 ? Math.max(4, (readyCount / totalCount) * 100) : null;

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
        Graph Generation
      </span>

      <h3 className="mb-3 text-2xl font-semibold tracking-tight text-zinc-900">
        正在为你生成学习图谱
      </h3>

      <div className="mb-8 w-full max-w-sm space-y-2 text-left">
        <p className="text-sm text-zinc-500">正在构建核心概念与知识依赖关系...</p>
        {totalCount > 0 && (
          <p className="text-sm text-zinc-500">
            {readyCount} / {totalCount} 个节点已完成
          </p>
        )}
      </div>

      <div className="h-2 w-full max-w-md overflow-hidden rounded-full bg-zinc-100">
        {progress !== null ? (
          <div
            className="h-full rounded-full bg-gradient-to-r from-teal-400 via-blue-500 to-cyan-400 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        ) : (
          <div className="h-full w-1/3 animate-pulse rounded-full bg-gradient-to-r from-teal-400 via-blue-500 to-cyan-400" />
        )}
      </div>
    </div>
  );
}
