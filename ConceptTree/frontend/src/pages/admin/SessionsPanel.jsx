import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Filter, GitCommit } from "lucide-react";

import { adminApi } from "../../services/adminApi";
import {
  Drawer,
  EmptyState,
  ErrorBlock,
  LoadingBlock,
  PageIntro,
  Panel,
  StatusBadge,
  TableShell,
  tableCellClass,
  tableHeadClass,
} from "./AdminUi";
import {
  formatDateTime,
  formatDuration,
  formatNumber,
  statusTone,
} from "./adminFormat";

const initialFilters = { userId: "", status: "", state: "" };

const TraceTimeline = ({ items }) => {
  if (!items.length) return <EmptyState>这个 Session 暂无追踪事件</EmptyState>;
  return (
    <ol className="space-y-0">
      {items.map((event, index) => (
        <li key={event.id} className="relative grid grid-cols-[28px_minmax(0,1fr)] gap-3 pb-5">
          {index < items.length - 1 ? <span className="absolute bottom-0 left-[13px] top-6 w-px bg-black/10" /> : null}
          <span className={`relative mt-1 flex h-7 w-7 items-center justify-center rounded-full ${event.status === "error" ? "bg-rose-100 text-rose-700" : "bg-[#fff0d6] text-[#b96515]"}`}>
            {event.status === "error" ? <AlertTriangle size={13} /> : <GitCommit size={13} />}
          </span>
          <div className="min-w-0 rounded-2xl border border-black/[0.075] bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-semibold text-[#2b2824]">{event.eventName}</p>
                <p className="mt-1 text-[11px] text-[#8d867d]">{event.eventType} · {formatDateTime(event.createdAt)}</p>
              </div>
              <StatusBadge tone={statusTone(event.status)}>{event.status}</StatusBadge>
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-[11px] text-[#716b63]">
              <span>耗时 {formatDuration(event.durationMs)}</span>
              {event.provider ? <span>{event.provider} / {event.model || "—"}</span> : null}
              {event.inputTokens || event.outputTokens ? <span>Tokens {formatNumber((event.inputTokens || 0) + (event.outputTokens || 0))}</span> : null}
              {event.retryCount ? <span>重试 {event.retryCount}</span> : null}
              {event.errorCode ? <span className="text-rose-700">{event.errorCode}</span> : null}
            </div>
            {event.attributes && Object.keys(event.attributes).length ? (
              <pre className="mt-3 overflow-x-auto rounded-xl bg-[#f7f5f0] p-3 text-[10px] leading-5 text-[#625c54] custom-scrollbar">
                {JSON.stringify(event.attributes, null, 2)}
              </pre>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
};

export default function SessionsPanel() {
  const [draftFilters, setDraftFilters] = useState(initialFilters);
  const [filters, setFilters] = useState(initialFilters);
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [trace, setTrace] = useState(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceLoadingMore, setTraceLoadingMore] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminApi.sessions({ limit: 50, ...filters });
      setItems(result.items || []);
      setCursor(result.nextCursor || null);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const loadMore = async () => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const result = await adminApi.sessions({ limit: 50, cursor, ...filters });
      setItems((current) => [...current, ...(result.items || [])]);
      setCursor(result.nextCursor || null);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoadingMore(false);
    }
  };

  const openTrace = async (session) => {
    setTrace({ session, items: [], nextCursor: null });
    setTraceLoading(true);
    try {
      setTrace(await adminApi.trace(session.id, { limit: 100 }));
    } catch (requestError) {
      setTrace({ session, items: [], error: requestError.message });
    } finally {
      setTraceLoading(false);
    }
  };

  const loadMoreTrace = async () => {
    if (!trace?.nextCursor || traceLoadingMore) return;
    setTraceLoadingMore(true);
    try {
      const result = await adminApi.trace(trace.session.id, {
        limit: 100,
        cursor: trace.nextCursor,
      });
      setTrace((current) => ({
        ...current,
        session: result.session,
        items: [...current.items, ...(result.items || [])],
        nextCursor: result.nextCursor || null,
      }));
    } catch (requestError) {
      setTrace((current) => ({ ...current, error: requestError.message }));
    } finally {
      setTraceLoadingMore(false);
    }
  };

  return (
    <div className="space-y-7">
      <PageIntro
        eyebrow="Control room / sessions"
        title="会话与追踪"
        description="查看深入学习 Session 状态，并进入每个 Session 的结构化 Trace 时间线。对话正文不会在列表中暴露。"
      />

      <Panel className="p-4">
        <form
          className="grid gap-3 md:grid-cols-[minmax(180px,1fr)_180px_180px_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            setFilters({ ...draftFilters });
          }}
        >
          <input
            value={draftFilters.userId}
            onChange={(event) => setDraftFilters((current) => ({ ...current, userId: event.target.value }))}
            placeholder="用户 ID"
            className="min-h-10 rounded-xl border border-black/10 bg-white px-3 text-xs outline-none focus:border-[#dc842c]"
          />
          <select
            value={draftFilters.status}
            onChange={(event) => setDraftFilters((current) => ({ ...current, status: event.target.value }))}
            className="min-h-10 rounded-xl border border-black/10 bg-white px-3 text-xs outline-none"
          >
            <option value="">全部状态</option>
            <option value="in_progress">进行中</option>
            <option value="completed">已完成</option>
            <option value="abandoned">已放弃</option>
          </select>
          <input
            value={draftFilters.state}
            onChange={(event) => setDraftFilters((current) => ({ ...current, state: event.target.value }))}
            placeholder="状态机 State"
            className="min-h-10 rounded-xl border border-black/10 bg-white px-3 text-xs outline-none focus:border-[#dc842c]"
          />
          <button type="submit" className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl bg-[#24211d] px-4 text-xs font-semibold text-white">
            <Filter size={14} />应用筛选
          </button>
        </form>
      </Panel>

      {loading ? <LoadingBlock label="正在读取 Session…" /> : null}
      {!loading && error ? <ErrorBlock error={error} onRetry={load} /> : null}
      {!loading && !error ? (
        <Panel className="overflow-hidden">
          {items.length ? (
            <>
              <TableShell>
                <thead><tr>
                  <th className={tableHeadClass}>Session</th>
                  <th className={tableHeadClass}>用户</th>
                  <th className={tableHeadClass}>学习内容</th>
                  <th className={tableHeadClass}>状态</th>
                  <th className={tableHeadClass}>轮次 / 测试</th>
                  <th className={tableHeadClass}>更新时间</th>
                </tr></thead>
                <tbody>
                  {items.map((session) => (
                    <tr key={session.id} tabIndex={0} onClick={() => openTrace(session)} onKeyDown={(event) => event.key === "Enter" && openTrace(session)} className="cursor-pointer bg-white hover:bg-[#fff8ec] focus:bg-[#fff8ec] focus:outline-none">
                      <td className={tableCellClass}><p className="max-w-44 truncate font-mono text-[11px]">{session.id}</p><p className="mt-1 text-[10px] text-[#918a80]">{formatDateTime(session.createdAt)}</p></td>
                      <td className={tableCellClass}><p className="font-medium">{session.user.email}</p><p className="mt-1 max-w-40 truncate font-mono text-[10px] text-[#918a80]">{session.user.id}</p></td>
                      <td className={tableCellClass}><p className="max-w-52 truncate font-medium">{session.node.name}</p><p className="mt-1 max-w-52 truncate text-[10px] text-[#918a80]">{session.plan.title}</p></td>
                      <td className={tableCellClass}><StatusBadge tone={statusTone(session.status)}>{session.status}</StatusBadge><p className="mt-1.5 text-[10px] text-[#918a80]">{session.state}</p></td>
                      <td className={tableCellClass}>{session.recentTurnCount} / {session.testResultCount}</td>
                      <td className={tableCellClass}>{formatDateTime(session.updatedAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </TableShell>
              {cursor ? <div className="flex justify-center p-4"><button type="button" onClick={loadMore} disabled={loadingMore} className="rounded-full border border-black/10 bg-white px-4 py-2 text-xs font-semibold hover:bg-[#f7f4ee] disabled:opacity-50">{loadingMore ? "加载中…" : "加载更多"}</button></div> : null}
            </>
          ) : <EmptyState>没有匹配的 Session</EmptyState>}
        </Panel>
      ) : null}

      <Drawer
        open={Boolean(trace)}
        onClose={() => setTrace(null)}
        title={trace?.session?.node?.name || "Session Trace"}
        subtitle={trace?.session?.id}
      >
        {traceLoading ? <LoadingBlock label="正在读取 Session Trace…" /> : null}
        {!traceLoading && trace?.error ? <ErrorBlock error={{ message: trace.error }} /> : null}
        {!traceLoading && trace && !trace.error ? (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                ["状态", trace.session.status],
                ["难度", trace.session.difficultyLevel],
                ["薄弱点", trace.session.weakPoints?.length || 0],
                ["测试", trace.session.testResults?.length || 0],
              ].map(([label, value]) => <div key={label} className="rounded-2xl border border-black/[0.08] bg-white p-3"><p className="truncate text-lg font-semibold">{value ?? "—"}</p><p className="mt-1 text-[10px] uppercase tracking-wider text-[#918a80]">{label}</p></div>)}
            </div>
            {trace.session.conversationSummary ? <Panel className="p-4"><p className="text-[10px] font-semibold uppercase tracking-wider text-[#918a80]">对话摘要</p><p className="mt-2 text-sm leading-6 text-[#5f5a53]">{trace.session.conversationSummary}</p></Panel> : null}
            <div>
              <h3 className="mb-4 text-sm font-semibold">事件时间线 · {trace.items.length}</h3>
              <TraceTimeline items={trace.items} />
              {trace.nextCursor ? <button type="button" onClick={loadMoreTrace} disabled={traceLoadingMore} className="w-full rounded-xl border border-black/10 bg-white py-2.5 text-xs font-semibold hover:bg-[#f7f4ee] disabled:opacity-50">{traceLoadingMore ? "加载中…" : "加载更多事件"}</button> : null}
            </div>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
