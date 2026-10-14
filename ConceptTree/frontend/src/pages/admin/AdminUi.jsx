import React, { useEffect } from "react";
import { AlertCircle, X } from "lucide-react";

export const Panel = ({ children, className = "" }) => (
  <section
    className={`rounded-[18px] border border-black/[0.08] bg-white shadow-[0_1px_2px_rgba(30,25,18,0.03)] ${className}`}
  >
    {children}
  </section>
);

export const MetricCard = ({ label, value, detail, accent = false }) => (
  <Panel className={`p-5 ${accent ? "bg-[#fff3df]" : ""}`}>
    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#918a80]">
      {label}
    </p>
    <p className="mt-3 break-words text-[clamp(1.35rem,3vw,2.35rem)] font-semibold tracking-[-0.055em] text-[#211f1b]">
      {value}
    </p>
    {detail ? <p className="mt-1 text-xs text-[#7b756d]">{detail}</p> : null}
  </Panel>
);

export const StatusBadge = ({ children, tone = "neutral" }) => {
  const tones = {
    success: "bg-emerald-50 text-emerald-700 ring-emerald-600/15",
    danger: "bg-rose-50 text-rose-700 ring-rose-600/15",
    warning: "bg-amber-50 text-amber-700 ring-amber-600/15",
    neutral: "bg-stone-100 text-stone-600 ring-stone-500/10",
  };
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset ${tones[tone] || tones.neutral}`}
    >
      {children ?? "—"}
    </span>
  );
};

export const PageIntro = ({ eyebrow, title, description, actions }) => (
  <header className="flex flex-col gap-5 border-b border-black/[0.07] pb-7 lg:flex-row lg:items-end lg:justify-between">
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#c46f19]">
        {eyebrow}
      </p>
      <h1 className="mt-2 text-[clamp(2rem,5vw,4.6rem)] font-semibold leading-[0.95] tracking-[-0.07em] text-[#1f1d19]">
        {title}
      </h1>
      {description ? (
        <p className="mt-4 max-w-2xl text-sm leading-6 text-[#756f66]">{description}</p>
      ) : null}
    </div>
    {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
  </header>
);

export const RangeSelect = ({ value, onChange }) => (
  <label className="inline-flex items-center gap-2 rounded-full border border-black/[0.1] bg-white px-3 py-2 text-xs font-medium text-[#5f5a53] shadow-sm">
    <span>范围</span>
    <select
      aria-label="数据范围"
      value={value}
      onChange={(event) => onChange(Number(event.target.value))}
      className="bg-transparent pr-1 font-semibold text-[#26231f] outline-none"
    >
      <option value={7}>近 7 天</option>
      <option value={30}>近 30 天</option>
      <option value={90}>近 90 天</option>
    </select>
  </label>
);

export const LoadingBlock = ({ label = "正在读取平台数据…" }) => (
  <Panel className="flex min-h-52 items-center justify-center p-8">
    <div className="text-center">
      <span className="mx-auto block h-7 w-7 animate-spin rounded-full border-2 border-[#ef9a3b] border-t-transparent" />
      <p className="mt-3 text-sm text-[#777168]">{label}</p>
    </div>
  </Panel>
);

export const ErrorBlock = ({ error, onRetry }) => (
  <Panel className="flex min-h-44 flex-col items-center justify-center p-8 text-center">
    <AlertCircle size={22} className="text-rose-500" />
    <p className="mt-3 text-sm font-medium text-[#352f2a]">数据读取失败</p>
    <p className="mt-1 max-w-lg text-xs leading-5 text-[#817a71]">
      {error?.message || "请稍后再试"}
    </p>
    {onRetry ? (
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-full bg-[#24211d] px-4 py-2 text-xs font-semibold text-white hover:bg-black"
      >
        重新加载
      </button>
    ) : null}
  </Panel>
);

export const EmptyState = ({ children = "暂无数据" }) => (
  <div className="flex min-h-40 items-center justify-center px-6 text-sm text-[#958e85]">
    {children}
  </div>
);

export const Drawer = ({ open, title, subtitle, onClose, children }) => {
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[80]" role="presentation">
      <button
        type="button"
        aria-label="关闭详情"
        className="absolute inset-0 bg-black/20 backdrop-blur-[2px]"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="absolute inset-y-0 right-0 flex w-full max-w-2xl flex-col border-l border-black/10 bg-[#fbfaf7] shadow-[-20px_0_60px_rgba(36,29,20,0.12)]"
      >
        <div className="flex items-start justify-between border-b border-black/[0.08] px-5 py-5 sm:px-7">
          <div className="min-w-0">
            <h2 className="truncate text-xl font-semibold tracking-[-0.035em] text-[#24211d]">
              {title}
            </h2>
            {subtitle ? <p className="mt-1 truncate text-xs text-[#817a71]">{subtitle}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="ml-4 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-black/10 bg-white text-[#777168] hover:text-black"
            aria-label="关闭"
          >
            <X size={17} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5 custom-scrollbar sm:px-7">
          {children}
        </div>
      </aside>
    </div>
  );
};

export const TableShell = ({ children }) => (
  <div className="overflow-x-auto custom-scrollbar">
    <table className="w-full min-w-[760px] border-collapse text-left text-sm">{children}</table>
  </div>
);

export const tableHeadClass =
  "border-b border-black/[0.08] bg-[#faf9f6] px-4 py-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#918a80]";
export const tableCellClass = "border-b border-black/[0.065] px-4 py-3.5 align-middle";
