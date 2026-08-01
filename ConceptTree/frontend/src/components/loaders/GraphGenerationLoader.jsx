import { useEffect, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { useLanguage } from "../../contexts/LanguageContext";

const STAGES = [
  { key: "parse", messageKey: "loader.graph.parse", startSec: 0 },
  { key: "recall", messageKey: "loader.graph.recall", startSec: 3 },
  { key: "graph", messageKey: "loader.graph.build", startSec: 10 },
  { key: "verify", messageKey: "loader.graph.verify", startSec: 20 },
];

const OVERTIME_THRESHOLD_SEC = 30;

function pickActiveStageIndex(elapsedSec) {
  let active = 0;
  for (let i = 0; i < STAGES.length; i += 1) {
    if (elapsedSec >= STAGES[i].startSec) active = i;
  }
  return active;
}

export default function GraphGenerationLoader({
  readyCount = 0,
  totalCount = 0,
}) {
  const { t } = useLanguage();
  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const interval = setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startedAt) / 1000));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  const activeIndex = pickActiveStageIndex(elapsedSec);
  const isOvertime = elapsedSec >= OVERTIME_THRESHOLD_SEC;
  const progress = totalCount > 0 ? Math.max(4, (readyCount / totalCount) * 100) : null;

  const subtitle = isOvertime
    ? t("loader.graph.overtime")
    : t("loader.graph.elapsed", { count: elapsedSec });

  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center overflow-hidden rounded-[28px] bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.08),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(244,247,250,0.99))] px-8 text-center">
      <span className="mb-4 rounded-full border border-blue-200 bg-white/90 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-blue-600">
        Graph Generation
      </span>

      <h3 className="mb-2 text-2xl font-semibold tracking-tight text-zinc-900">
        {t("loader.graph.title")}
      </h3>
      <p className="mb-8 text-sm text-zinc-500">{subtitle}</p>

      <ol className="mb-8 w-full max-w-sm space-y-3 text-left">
        {STAGES.map((stage, index) => {
          const done = index < activeIndex;
          const active = index === activeIndex;
          return (
            <li key={stage.key} className="flex items-center gap-3">
              {done ? (
                <CheckCircle2 size={18} className="text-teal-500" />
              ) : active ? (
                <span className="relative flex h-[18px] w-[18px] items-center justify-center">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-40" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
                </span>
              ) : (
                <span className="inline-flex h-[18px] w-[18px] items-center justify-center rounded-full border border-zinc-200 bg-white" />
              )}
              <span
                className={
                  done
                    ? "text-sm text-zinc-500"
                    : active
                      ? "text-sm font-semibold text-zinc-900"
                      : "text-sm text-zinc-300"
                }
              >
                {t(stage.messageKey)}
              </span>
            </li>
          );
        })}
      </ol>

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

      {totalCount > 0 && (
        <p className="mt-3 text-xs text-zinc-400">
          {t("loader.graph.nodes", { ready: readyCount, total: totalCount })}
        </p>
      )}
    </div>
  );
}
