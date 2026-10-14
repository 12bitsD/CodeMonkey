import React, { useCallback, useEffect, useState } from "react";
import { KeyRound, Lock, ShieldAlert } from "lucide-react";

import { ADMIN_SESSION_EXPIRED_EVENT, adminApi } from "../../services/adminApi";

const Checking = () => (
  <div className="flex min-h-screen items-center justify-center bg-[#f5f2ec]">
    <div className="text-center">
      <span className="mx-auto block h-8 w-8 animate-spin rounded-full border-2 border-[#ed9233] border-t-transparent" />
      <p className="mt-4 text-sm text-[#777168]">正在验证管理员会话…</p>
    </div>
  </div>
);

export default function AdminAccessGate({ children }) {
  const [state, setState] = useState("checking");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const checkSession = useCallback(async () => {
    setState("checking");
    try {
      await adminApi.me();
      setState("granted");
    } catch (requestError) {
      setState(requestError?.status === 403 ? "denied" : "locked");
    }
  }, []);

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  useEffect(() => {
    const handleExpired = () => {
      setPassword("");
      setError("管理员会话已过期，请重新验证。请放心，你的普通登录状态仍然保留。");
      setState("locked");
    };
    window.addEventListener(ADMIN_SESSION_EXPIRED_EVENT, handleExpired);
    return () => window.removeEventListener(ADMIN_SESSION_EXPIRED_EVENT, handleExpired);
  }, []);

  const unlock = async (event) => {
    event.preventDefault();
    if (!password) return;
    setSubmitting(true);
    setError("");
    try {
      await adminApi.elevate(password);
      setPassword("");
      setState("granted");
    } catch (requestError) {
      setError(requestError?.message || "验证失败，请检查密码和管理员权限");
    } finally {
      setSubmitting(false);
    }
  };

  const lock = async () => {
    await adminApi.logout().catch(() => {});
    setPassword("");
    setState("locked");
  };

  if (state === "checking") return <Checking />;
  if (state === "granted") return children({ lock });

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f5f2ec] p-5">
      <div className="w-full max-w-md rounded-[28px] border border-black/[0.08] bg-[#fffdf9] p-7 shadow-[0_24px_80px_rgba(49,38,24,0.12)] sm:p-9">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#24211d] text-white">
          {state === "denied" ? <ShieldAlert size={22} /> : <Lock size={22} />}
        </div>
        <p className="mt-8 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#c46f19]">
          Private control room
        </p>
        <h1 className="mt-2 text-4xl font-semibold tracking-[-0.06em] text-[#211f1b]">
          {state === "denied" ? "没有管理员权限" : "管理员验证"}
        </h1>
        <p className="mt-4 text-sm leading-6 text-[#756f66]">
          {state === "denied"
            ? "当前账户没有管理员角色。这个页面没有公开入口，权限由服务器数据库控制。"
            : "请重新输入当前账户密码，开启一个独立的短时管理员会话。"}
        </p>

        {state === "denied" ? (
          <a
            href="/"
            className="mt-8 inline-flex rounded-full bg-[#24211d] px-5 py-2.5 text-sm font-semibold text-white hover:bg-black"
          >
            返回学习平台
          </a>
        ) : (
          <form onSubmit={unlock} className="mt-8 space-y-4">
            <label className="block">
              <span className="mb-2 block text-xs font-semibold text-[#5f5a53]">账户密码</span>
              <div className="flex items-center rounded-xl border border-black/[0.12] bg-white px-3 focus-within:border-[#dc842c] focus-within:ring-4 focus-within:ring-[#ef9a3b]/10">
                <KeyRound size={16} className="text-[#918a80]" />
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  className="min-h-12 w-full bg-transparent px-3 text-sm outline-none"
                  placeholder="输入当前登录账户的密码"
                  autoFocus
                />
              </div>
            </label>
            {error ? (
              <p role="alert" className="rounded-xl bg-rose-50 px-4 py-3 text-xs leading-5 text-rose-700">
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={submitting || !password}
              className="min-h-12 w-full rounded-xl bg-[#24211d] px-4 text-sm font-semibold text-white hover:bg-black disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "正在验证…" : "进入控制台"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
