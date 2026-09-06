import { useEffect, useState } from "react";
import { Check, Loader2, Lock } from "lucide-react";
import { useLanguage } from "../../contexts/LanguageContext";

const ANALYSIS_STAGES = [
  "loader.analysis.boundary",
  "loader.analysis.background",
  "loader.analysis.questions",
];

export default function GoalAnalysisLoader({ step = 0 }) {
  const { t } = useLanguage();
  const [elapsedSec, setElapsedSec] = useState(0);
  const activeIndex = Math.min(Math.max(step, 0), ANALYSIS_STAGES.length - 1);

  useEffect(() => {
    const startedAt = Date.now();
    const interval = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startedAt) / 1000));
    }, 500);
    return () => window.clearInterval(interval);
  }, []);

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
          {t("loader.analysis.title")}
        </h3>
        <p className="mt-2 text-[0.8125rem] leading-5 text-[#6f6e6b]">
          {t("loader.analysis.help")}
        </p>

        <div className="mt-7 rounded-lg border border-black/[0.08] bg-[#fbfbfa] p-2">
          <div className="mb-1 flex items-center justify-between px-2 py-1.5 text-[0.6875rem] font-medium text-[#8f8e8b]">
            <span>{t("loader.progress.estimated")}</span>
            <span className="tabular-nums">{activeIndex + 1}/{ANALYSIS_STAGES.length}</span>
          </div>
          <ol className="space-y-0.5">
            {ANALYSIS_STAGES.map((messageKey, index) => {
              const done = index < activeIndex;
              const active = index === activeIndex;
              return (
                <li
                  key={messageKey}
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
                  <span className={active ? "font-medium" : "font-normal"}>{t(messageKey)}</span>
                </li>
              );
            })}
          </ol>
        </div>

        <div className="mt-5 flex items-start gap-2.5 border-t border-black/[0.07] pt-4 text-xs leading-5 text-[#8f8e8b]">
          <Lock size={14} strokeWidth={1.7} className="mt-0.5 shrink-0" />
          <p>{t("loader.analysis.disclosure")}</p>
        </div>
      </div>
    </div>
  );
}
