import React from "react";
import {
  Activity,
  BrainCircuit,
  LayoutDashboard,
  Lock,
  MessagesSquare,
  Users,
} from "lucide-react";

const navigation = [
  { id: "overview", label: "总览", icon: LayoutDashboard },
  { id: "users", label: "用户", icon: Users },
  { id: "sessions", label: "会话与追踪", icon: MessagesSquare },
  { id: "ai-usage", label: "AI 用量", icon: BrainCircuit },
  { id: "system", label: "系统", icon: Activity },
];

const RailButton = ({ active, label, icon: Icon, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    aria-label={label}
    aria-current={active ? "page" : undefined}
    className={`group relative flex h-11 w-11 items-center justify-center rounded-[14px] transition-colors ${
      active
        ? "bg-[#24211d] text-white shadow-[0_7px_18px_rgba(42,34,24,0.2)]"
        : "text-[#817a71] hover:bg-black/[0.055] hover:text-[#24211d]"
    }`}
  >
    <Icon size={18} strokeWidth={1.9} />
    <span className="pointer-events-none absolute left-[calc(100%+10px)] z-50 hidden whitespace-nowrap rounded-lg bg-[#24211d] px-2.5 py-1.5 text-[11px] font-medium text-white shadow-lg group-hover:block group-focus-visible:block md:block md:opacity-0 md:group-hover:opacity-100 md:group-focus-visible:opacity-100">
      {label}
    </span>
  </button>
);

export default function AdminShell({ active, onNavigate, onLock, children }) {
  return (
    <div className="min-h-screen bg-[#f5f2ec] text-[#24211d]">
      <aside className="fixed inset-y-0 left-0 z-50 hidden w-20 flex-col items-center border-r border-black/[0.07] bg-[#fbfaf7] py-5 md:flex">
        <div className="flex h-11 w-11 items-center justify-center rounded-[14px] bg-[#ef9a3b] text-lg font-black tracking-[-0.08em] text-[#211f1b] shadow-sm">
          CT
        </div>
        <nav className="mt-9 flex flex-1 flex-col gap-2" aria-label="管理员菜单">
          {navigation.map((item) => (
            <RailButton
              key={item.id}
              {...item}
              active={active === item.id}
              onClick={() => onNavigate(item.id)}
            />
          ))}
        </nav>
        <RailButton label="锁定后台" icon={Lock} onClick={onLock} />
      </aside>

      <header className="sticky top-0 z-40 flex h-16 items-center gap-2 overflow-x-auto border-b border-black/[0.07] bg-[#fbfaf7]/95 px-4 backdrop-blur-xl md:hidden">
        <div className="mr-2 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#ef9a3b] text-xs font-black">
          CT
        </div>
        {navigation.map((item) => (
          <button
            type="button"
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`flex h-9 shrink-0 items-center gap-2 rounded-full px-3 text-xs font-semibold ${
              active === item.id ? "bg-[#24211d] text-white" : "text-[#746e65]"
            }`}
          >
            <item.icon size={15} />
            {item.label}
          </button>
        ))}
        <button
          type="button"
          onClick={onLock}
          className="ml-auto flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-black/10 bg-white text-[#746e65]"
          aria-label="锁定后台"
        >
          <Lock size={15} />
        </button>
      </header>

      <main className="min-h-screen md:pl-20">
        <div className="mx-auto w-full max-w-[1520px] px-4 py-7 sm:px-7 lg:px-10 lg:py-10">
          {children}
        </div>
      </main>
    </div>
  );
}
