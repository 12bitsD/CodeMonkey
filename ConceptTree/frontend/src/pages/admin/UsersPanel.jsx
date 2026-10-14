import React, { useCallback, useEffect, useState } from "react";
import { Search, User } from "lucide-react";

import { adminApi } from "../../services/adminApi";
import {
  Drawer,
  EmptyState,
  ErrorBlock,
  LoadingBlock,
  PageIntro,
  Panel,
  TableShell,
  tableCellClass,
  tableHeadClass,
} from "./AdminUi";
import { formatDateTime, formatNumber } from "./adminFormat";

export default function UsersPanel() {
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminApi.users({ limit: 50, query: appliedQuery });
      setItems(result.items || []);
      setCursor(result.nextCursor || null);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [appliedQuery]);

  useEffect(() => {
    load();
  }, [load]);

  const loadMore = async () => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const result = await adminApi.users({
        limit: 50,
        query: appliedQuery,
        cursor,
      });
      setItems((current) => [...current, ...(result.items || [])]);
      setCursor(result.nextCursor || null);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoadingMore(false);
    }
  };

  const openDetail = async (user) => {
    setDetail({ ...user, pending: true });
    setDetailLoading(true);
    try {
      setDetail(await adminApi.user(user.id));
    } catch (requestError) {
      setDetail({ ...user, error: requestError.message });
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="space-y-7">
      <PageIntro
        eyebrow="Control room / users"
        title="用户"
        description="查看用户规模、活跃时间以及计划、深入学习和笔记数量。邮箱默认脱敏。"
        actions={(
          <form
            className="flex items-center rounded-full border border-black/[0.1] bg-white pl-3 shadow-sm"
            onSubmit={(event) => {
              event.preventDefault();
              setAppliedQuery(query.trim());
            }}
          >
            <Search size={15} className="text-[#918a80]" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="用户 ID 或邮箱"
              className="h-10 w-44 bg-transparent px-2 text-xs outline-none sm:w-56"
            />
            <button type="submit" className="mr-1 rounded-full bg-[#24211d] px-3 py-2 text-xs font-semibold text-white">
              搜索
            </button>
          </form>
        )}
      />

      {loading ? <LoadingBlock label="正在读取用户数据…" /> : null}
      {!loading && error ? <ErrorBlock error={error} onRetry={load} /> : null}
      {!loading && !error ? (
        <Panel className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-black/[0.07] px-5 py-4">
            <div>
              <h2 className="font-semibold tracking-[-0.025em]">用户目录</h2>
              <p className="mt-1 text-xs text-[#817a71]">当前已加载 {formatNumber(items.length)} 位</p>
            </div>
          </div>
          {items.length ? (
            <>
              <TableShell>
                <thead>
                  <tr>
                    <th className={tableHeadClass}>用户</th>
                    <th className={tableHeadClass}>最近活跃</th>
                    <th className={tableHeadClass}>计划</th>
                    <th className={tableHeadClass}>深入学习</th>
                    <th className={tableHeadClass}>笔记</th>
                    <th className={tableHeadClass}>注册时间</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((user) => (
                    <tr
                      key={user.id}
                      tabIndex={0}
                      onClick={() => openDetail(user)}
                      onKeyDown={(event) => event.key === "Enter" && openDetail(user)}
                      className="cursor-pointer bg-white transition-colors hover:bg-[#fff8ec] focus:bg-[#fff8ec] focus:outline-none"
                    >
                      <td className={tableCellClass}>
                        <p className="font-semibold text-[#2b2824]">{user.email}</p>
                        <p className="mt-1 max-w-56 truncate font-mono text-[10px] text-[#9a938a]">{user.id}</p>
                      </td>
                      <td className={tableCellClass}>{formatDateTime(user.lastActiveAt)}</td>
                      <td className={tableCellClass}>{formatNumber(user.planCount)}</td>
                      <td className={tableCellClass}>{formatNumber(user.deepSessionCount)}</td>
                      <td className={tableCellClass}>{formatNumber(user.noteCount)}</td>
                      <td className={tableCellClass}>{formatDateTime(user.createdAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </TableShell>
              {cursor ? (
                <div className="flex justify-center p-4">
                  <button
                    type="button"
                    onClick={loadMore}
                    disabled={loadingMore}
                    className="rounded-full border border-black/10 bg-white px-4 py-2 text-xs font-semibold hover:bg-[#f7f4ee] disabled:opacity-50"
                  >
                    {loadingMore ? "加载中…" : "加载更多"}
                  </button>
                </div>
              ) : null}
            </>
          ) : (
            <EmptyState>没有匹配的用户</EmptyState>
          )}
        </Panel>
      ) : null}

      <Drawer
        open={Boolean(detail)}
        onClose={() => setDetail(null)}
        title={detail?.email || "用户详情"}
        subtitle={detail?.id}
      >
        {detailLoading ? <LoadingBlock label="正在读取用户详情…" /> : null}
        {!detailLoading && detail?.error ? <ErrorBlock error={{ message: detail.error }} /> : null}
        {!detailLoading && detail && !detail.error ? (
          <div className="space-y-5">
            <div className="flex items-center gap-3 rounded-2xl bg-[#fff1db] p-4">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#ef9a3b] text-[#24211d]"><User size={20} /></span>
              <div>
                <p className="font-semibold">{detail.email}</p>
                <p className="mt-0.5 text-xs text-[#756f66]">注册于 {formatDateTime(detail.createdAt)}</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                ["计划", detail.planCount],
                ["Session", detail.deepSessionCount],
                ["笔记", detail.noteCount],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-black/[0.08] bg-white p-4 text-center">
                  <p className="text-2xl font-semibold tracking-[-0.04em]">{formatNumber(value)}</p>
                  <p className="mt-1 text-[10px] uppercase tracking-wider text-[#918a80]">{label}</p>
                </div>
              ))}
            </div>
            <Panel className="p-5">
              <h3 className="text-sm font-semibold">学习画像</h3>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                {[
                  ["职业", detail.profile?.occupation],
                  ["教育背景", detail.profile?.education],
                  ["编程水平", detail.profile?.programmingLevel],
                  ["数学水平", detail.profile?.mathLevel],
                  ["已掌握知识", `${formatNumber(detail.profile?.masteredKnowledgeCount)} 项`],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-xs text-[#918a80]">{label}</dt>
                    <dd className="mt-1 font-medium text-[#352f2a]">{value || "未填写"}</dd>
                  </div>
                ))}
              </dl>
            </Panel>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
