import React, { useCallback, useEffect, useMemo, useState } from "react";

import { adminApi } from "../../services/adminApi";
import {
  ErrorBlock,
  LoadingBlock,
  MetricCard,
  PageIntro,
  Panel,
  RangeSelect,
} from "./AdminUi";
import {
  dateRangeForDays,
  formatNumber,
  formatPercent,
} from "./adminFormat";

const ActivityChart = ({ items }) => {
  const max = Math.max(
    1,
    ...items.flatMap((item) => [item.activeUsers || 0, item.deepSessions || 0]),
  );
  return (
    <Panel className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-black/[0.07] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-semibold tracking-[-0.025em]">学习活动趋势</h2>
          <p className="mt-1 text-xs text-[#817a71]">活跃用户与深入学习 Session</p>
        </div>
        <div className="flex gap-4 text-[11px] text-[#756f66]">
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-[#24211d]" />活跃用户</span>
          <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-[#ef9a3b]" />深入学习</span>
        </div>
      </div>
      <div className="overflow-x-auto px-5 pb-5 pt-7 custom-scrollbar">
        <div className="flex h-56 min-w-[620px] items-end gap-2" role="img" aria-label="学习活动柱状图">
          {items.map((item) => (
            <div key={item.day} className="group flex h-full min-w-4 flex-1 flex-col justify-end">
              <div className="flex h-[calc(100%-28px)] items-end justify-center gap-0.5">
                <div
                  className="w-[42%] rounded-t-md bg-[#24211d] transition-opacity group-hover:opacity-75"
                  style={{ height: `${Math.max(2, (item.activeUsers / max) * 100)}%` }}
                  title={`${item.activeUsers} 位活跃用户`}
                />
                <div
                  className="w-[42%] rounded-t-md bg-[#ef9a3b] transition-opacity group-hover:opacity-75"
                  style={{ height: `${Math.max(2, (item.deepSessions / max) * 100)}%` }}
                  title={`${item.deepSessions} 个深入学习 Session`}
                />
              </div>
              <span className="mt-2 truncate text-center text-[9px] text-[#9a938a]">
                {new Date(item.day).toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" })}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
};

export default function OverviewPanel() {
  const [days, setDays] = useState(7);
  const [data, setData] = useState(null);
  const [series, setSeries] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const range = useMemo(() => dateRangeForDays(days), [days]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overview, timeseries] = await Promise.all([
        adminApi.overview(range),
        adminApi.timeseries(range),
      ]);
      setData(overview);
      setSeries(timeseries.items || []);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-7">
      <PageIntro
        eyebrow="Control room / overview"
        title="平台总览"
        description="从产品视角查看增长、学习活跃、深入学习完成率与 AI 调用情况。数据读取会写入管理员审计日志。"
        actions={<RangeSelect value={days} onChange={setDays} />}
      />
      {loading ? <LoadingBlock /> : null}
      {!loading && error ? <ErrorBlock error={error} onRetry={load} /> : null}
      {!loading && data ? (
        <>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <MetricCard label="总用户" value={formatNumber(data.totalUsers)} detail={`期间新增 ${formatNumber(data.newUsers)}`} accent />
            <MetricCard label="活跃用户" value={formatNumber(data.activeUsers)} detail={`近 ${days} 天`} />
            <MetricCard label="深入学习" value={formatNumber(data.deepSessions)} detail={`${formatNumber(data.completedSessions)} 个已完成`} />
            <MetricCard label="完成率" value={formatPercent(data.completionRate)} detail="深入学习 Session" />
            <MetricCard label="新建计划" value={formatNumber(data.plansCreated)} detail={`${formatNumber(data.activePlans)} 个活跃计划`} />
            <MetricCard label="学习行为" value={formatNumber(data.learningEvents)} detail={`${formatNumber(data.notesCreated)} 条笔记`} />
            <MetricCard label="AI Tokens" value={formatNumber(data.totalTokens)} detail={data.costTrackingAvailable ? `$${Number(data.estimatedCostUsd).toFixed(4)} 估算` : "费用定价尚未配置"} />
            <MetricCard label="追踪错误" value={formatNumber(data.traceErrors)} detail="Session Trace 错误事件" />
          </div>
          <ActivityChart items={series} />
        </>
      ) : null}
    </div>
  );
}
