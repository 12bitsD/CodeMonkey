import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { useLanguage } from "../../contexts/LanguageContext";

const STAGES = [
  { key: "parse", messageKey: "loader.graph.parse", startSec: 0 },
  { key: "recall", messageKey: "loader.graph.recall", startSec: 3 },
  { key: "graph", messageKey: "loader.graph.build", startSec: 10 },
  { key: "verify", messageKey: "loader.graph.verify", startSec: 20 },
];

const OVERTIME_THRESHOLD_SEC = 30;

function pickActiveStageIndex(elapsedSec, readyCount, totalCount) {
  let active = 0;
  for (let i = 0; i < STAGES.length; i += 1) {
    if (elapsedSec >= STAGES[i].startSec) active = i;
  }
  if (readyCount > 0) active = Math.max(active, 2);
  if (totalCount > 0 && readyCount >= totalCount) active = STAGES.length - 1;
  return active;
}

export default function GraphGenerationLoader({ readyCount = 0, totalCount = 0 }) {
  const { t } = useLanguage();
  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const interval = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startedAt) / 1000));
    }, 500);
    return () => window.clearInterval(interval);
  }, []);

  const activeIndex = pickActiveStageIndex(elapsedSec, readyCount, totalCount);
  const isOvertime = elapsedSec >= OVERTIME_THRESHOLD_SEC;
  const hasLiveCount = totalCount > 0;
  const progress = hasLiveCount ? Math.min(100, Math.max(0, (readyCount / totalCount) * 100)) : null;

  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#fbfbfa] px-5 py-8 sm:px-8">
      <div className="w-full max-w-xl rounded-xl border border-black/[0.1] bg-white p-5 shadow-[0_1px_2px_rgba(15,15,15,0.04)] sm:p-7">
        <div className="mb-6 flex items-center justify-between gap-4">
          <span className="inline-flex items-center gap-2 text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-[#6f6e6b]">
            <span className="h-2 w-2 rounded-full bg-[#2383e2] shadow-[0_0_0_3px_rgba(35,131,226,0.1)]" />
            {t("loader.status.running")}
          </span>
          <span className="tabular-nums text-xs text-[#8f8e8b]">
            {t("loader.progress.elapsed", { count: elapsedSec })}
          </span>
        </div>

        <h3 className="text-xl font-semibold leading-tight tracking-[-0.018em] text-[#202020] sm:text-[1.375rem]">
          {t("loader.graph.title")}
        </h3>
        <p className="mt-2 text-[0.8125rem] leading-5 text-[#6f6e6b]">
          {isOvertime ? t("loader.graph.overtime") : t("loader.graph.help")}
        </p>

        <div className="mt-7">
          <ol className="space-y-0.5 rounded-lg border border-black/[0.08] bg-[#fbfbfa] p-2">
            {STAGES.map((stage, index) => {
              const done = index < activeIndex;
              const active = index === activeIndex;
              return (
                <li
                  key={stage.key}
                  className={`flex min-h-10 items-center gap-3 rounded-md px-2.5 py-2 text-[0.8125rem] ${
                    active ? "bg-white text-[#202020] shadow-[0_1px_2px_rgba(15,15,15,0.05)]" : "text-[#8f8e8b]"
                  }`}
                >
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center">
                    {done ? (
                      <Check size={15} strokeWidth={2} className="text-[#448361]" />
                    ) : active ? (
                      <Loader2 size={15} strokeWidth={1.8} className="animate-spin text-[#2383e2]" />
                    ) : (
                      <span className="h-1.5 w-1.5 rounded-full bg-black/[0.14]" />
                    )}
                  </span>
                  <span className={active ? "font-medium" : "font-normal"}>{t(stage.messageKey)}</span>
                </li>
              );
            })}
          </ol>
        </div>

        <div className="mt-5">
          <div className="h-1.5 overflow-hidden rounded-full bg-black/[0.06]" aria-hidden="true">
            {progress === null ? (
              <div className="h-full w-1/4 animate-pulse rounded-full bg-black/40" />
            ) : (
              <div
                className="h-full rounded-full bg-[#202020] transition-[width] duration-200 ease-[var(--ease-out-apple)]"
                style={{ width: `${progress}%` }}
              />
            )}
          </div>
          <div className="mt-3 flex items-start justify-between gap-4 text-xs leading-5 text-[#8f8e8b]">
            <p>{t("loader.graph.disclosure")}</p>
            <span className="shrink-0">{t("loader.progress.estimated")}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
