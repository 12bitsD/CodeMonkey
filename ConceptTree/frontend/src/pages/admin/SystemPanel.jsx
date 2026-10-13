import React, { useCallback, useEffect, useState } from "react";
import { Database, RefreshCw, ServerCog } from "lucide-react";

import { adminApi } from "../../services/adminApi";
import {
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
import { formatDuration, formatNumber } from "./adminFormat";

export default function SystemPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await adminApi.systemHealth());
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const routes = Object.entries(data?.requests || {})
    .map(([route, metrics]) => ({ route, ...metrics }))
    .sort((a, b) => b.count - a.count);
  const dbErrors = Object.entries(data?.dbErrorCounts || {});

  return (
    <div className="space-y-7">
      <PageIntro
        eyebrow="Control room / system"
        title="系统"
        description="查看当前 backend 进程内的请求计数、延迟和数据库错误。容器重启后这些运行时指标会重新计数。"
        actions={(
          <button type="button" onClick={load} disabled={loading} className="inline-flex min-h-10 items-center gap-2 rounded-full border border-black/10 bg-white px-4 text-xs font-semibold shadow-sm hover:bg-[#faf8f3] disabled:opacity-50">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />刷新
          </button>
        )}
      />
      {loading ? <LoadingBlock label="正在读取系统指标…" /> : null}
      {!loading && error ? <ErrorBlock error={error} onRetry={load} /> : null}
      {!loading && data ? (
        <>
          <div className="grid gap-3 lg:grid-cols-2">
            <Panel className="p-5">
              <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700"><ServerCog size={18} /></span><div><h2 className="font-semibold">Backend 运行时</h2><p className="text-xs text-[#817a71]">{formatNumber(routes.length)} 个已观测路由</p></div></div>
            </Panel>
            <Panel className="p-5">
              <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#fff0d6] text-[#b96515]"><Database size={18} /></span><div><h2 className="font-semibold">数据库错误</h2><p className="text-xs text-[#817a71]">{formatNumber(dbErrors.reduce((sum, [, count]) => sum + count, 0))} 次累计错误</p></div></div>
            </Panel>
          </div>
          {dbErrors.length ? <Panel className="p-5"><h2 className="text-sm font-semibold">数据库错误类型</h2><div className="mt-4 flex flex-wrap gap-2">{dbErrors.map(([code, count]) => <StatusBadge key={code} tone="danger">{code}: {count}</StatusBadge>)}</div></Panel> : null}
          <Panel className="overflow-hidden">
            <div className="border-b border-black/[0.07] px-5 py-4"><h2 className="font-semibold tracking-[-0.025em]">请求指标</h2><p className="mt-1 text-xs text-[#817a71]">按当前进程累计请求量排序</p></div>
            {routes.length ? <TableShell>
              <thead><tr><th className={tableHeadClass}>路由</th><th className={tableHeadClass}>请求</th><th className={tableHeadClass}>5xx</th><th className={tableHeadClass}>平均延迟</th><th className={tableHeadClass}>最大延迟</th></tr></thead>
              <tbody>{routes.map((route) => <tr key={route.route}><td className={`${tableCellClass} font-mono text-[11px]`}>{route.route}</td><td className={tableCellClass}>{formatNumber(route.count)}</td><td className={tableCellClass}><StatusBadge tone={route.errorCount ? "danger" : "success"}>{route.errorCount}</StatusBadge></td><td className={tableCellClass}>{formatDuration(route.avgLatencyMs)}</td><td className={tableCellClass}>{formatDuration(route.maxLatencyMs)}</td></tr>)}</tbody>
            </TableShell> : <EmptyState>当前进程还没有请求指标</EmptyState>}
          </Panel>
        </>
      ) : null}
    </div>
  );
}
