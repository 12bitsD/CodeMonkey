import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Coins } from "lucide-react";

import { adminApi } from "../../services/adminApi";
import {
  EmptyState,
  ErrorBlock,
  LoadingBlock,
  MetricCard,
  PageIntro,
  Panel,
  RangeSelect,
  StatusBadge,
  TableShell,
  tableCellClass,
  tableHeadClass,
} from "./AdminUi";
import { dateRangeForDays, formatDuration, formatNumber } from "./adminFormat";

export default function AiUsagePanel() {
  const [days, setDays] = useState(7);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const range = useMemo(() => dateRangeForDays(days), [days]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminApi.aiUsage(range);
      setModels(result.models || []);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    load();
  }, [load]);

  const totals = models.reduce(
    (sum, model) => ({
      calls: sum.calls + model.calls,
      errors: sum.errors + model.errors,
      tokens: sum.tokens + model.inputTokens + model.outputTokens,
      cost: sum.cost + model.estimatedCostUsd,
      priced: sum.priced || model.costTrackingAvailable,
    }),
    { calls: 0, errors: 0, tokens: 0, cost: 0, priced: false },
  );

  return (
    <div className="space-y-7">
      <PageIntro
        eyebrow="Control room / AI usage"
        title="AI 用量"
        description="按 Provider 与模型查看调用量、错误、Token 和延迟。费用只有在存在经过验证的定价记录时才展示。"
        actions={<RangeSelect value={days} onChange={setDays} />}
      />
      {loading ? <LoadingBlock label="正在汇总 AI 用量…" /> : null}
      {!loading && error ? <ErrorBlock error={error} onRetry={load} /> : null}
      {!loading && !error ? (
        <>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <MetricCard label="调用次数" value={formatNumber(totals.calls)} accent />
            <MetricCard label="错误次数" value={formatNumber(totals.errors)} detail={totals.calls ? `${((totals.errors / totals.calls) * 100).toFixed(1)}% 错误率` : "暂无调用"} />
            <MetricCard label="Token 总量" value={formatNumber(totals.tokens)} />
            <MetricCard label="估算成本" value={totals.priced ? `$${totals.cost.toFixed(4)}` : "未配置"} detail={totals.priced ? "仅统计有定价记录的调用" : "不会将未知成本显示为 0"} />
          </div>
          <Panel className="overflow-hidden">
            <div className="flex items-center gap-3 border-b border-black/[0.07] px-5 py-4">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#fff0d6] text-[#b96515]"><Coins size={17} /></span>
              <div><h2 className="font-semibold tracking-[-0.025em]">模型明细</h2><p className="mt-0.5 text-xs text-[#817a71]">近 {days} 天</p></div>
            </div>
            {models.length ? (
              <TableShell>
                <thead><tr>
                  <th className={tableHeadClass}>Provider / 模型</th>
                  <th className={tableHeadClass}>调用</th>
                  <th className={tableHeadClass}>错误</th>
                  <th className={tableHeadClass}>输入 Tokens</th>
                  <th className={tableHeadClass}>输出 Tokens</th>
                  <th className={tableHeadClass}>平均延迟</th>
                  <th className={tableHeadClass}>成本</th>
                </tr></thead>
                <tbody>{models.map((model) => (
                  <tr key={`${model.provider}:${model.model}`}>
                    <td className={tableCellClass}><p className="font-semibold">{model.model || "未标记模型"}</p><p className="mt-1 text-[10px] uppercase tracking-wider text-[#918a80]">{model.provider}</p></td>
                    <td className={tableCellClass}>{formatNumber(model.calls)}</td>
                    <td className={tableCellClass}><StatusBadge tone={model.errors ? "danger" : "success"}>{formatNumber(model.errors)}</StatusBadge></td>
                    <td className={tableCellClass}>{formatNumber(model.inputTokens)}</td>
                    <td className={tableCellClass}>{formatNumber(model.outputTokens)}</td>
                    <td className={tableCellClass}>{formatDuration(model.avgDurationMs)}</td>
                    <td className={tableCellClass}>{model.costTrackingAvailable ? `$${Number(model.estimatedCostUsd).toFixed(4)}` : <span className="text-[#918a80]">未配置</span>}</td>
                  </tr>
                ))}</tbody>
              </TableShell>
            ) : <EmptyState>当前范围内没有 AI 调用记录</EmptyState>}
          </Panel>
        </>
      ) : null}
    </div>
  );
}
