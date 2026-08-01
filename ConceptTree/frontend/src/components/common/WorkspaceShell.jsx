import React, { useState } from "react";
import {
  BookOpen,
  ChevronRight,
  Home,
  LogIn,
  LogOut,
  Menu,
  Plus,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePlanContext } from "../../contexts/PlanContext";
import LanguageToggle from "./LanguageToggle";
import { compactPlanTitle } from "../../utils/planTitle";
import learningMasterMark from "../../assets/branding/learningmaster-mark.png";

const NavButton = ({ active = false, icon: Icon, label, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    className={`group flex min-h-9 w-full items-center gap-2.5 rounded-md px-2.5 text-left text-sm transition-[background-color,color,transform] duration-150 active:scale-[0.99] ${
      active
        ? "bg-black/[0.055] font-medium text-[#202020]"
        : "text-[#5f5e5b] hover:bg-black/[0.04] hover:text-[#202020]"
    }`}
  >
    <Icon size={16} strokeWidth={1.8} aria-hidden="true" />
    <span className="min-w-0 flex-1 truncate">{label}</span>
  </button>
);

const SidebarContent = ({ active, onNavigate, onClose }) => {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();
  const { plans } = usePlanContext();
  const { t } = useLanguage();
  const recentPlans = plans
    .filter((plan) => plan.status === "active" || plan.status === "paused")
    .slice(0, 5);

  const go = (href) => {
    onNavigate?.();
    navigate(href);
  };

  const handleLogout = async () => {
    await logout();
    go("/");
  };

  return (
    <div className="flex h-full flex-col bg-[var(--color-sidebar)]">
      <div className="flex h-14 items-center gap-2 px-3">
        <button
          type="button"
          onClick={() => go("/")}
          className="group flex min-w-0 flex-1 items-center gap-2 rounded-md px-1.5 py-1.5 text-left hover:bg-black/[0.035]"
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white p-0.5 shadow-[0_1px_2px_rgba(0,0,0,0.08)] ring-1 ring-black/[0.08]">
            <img
              src={learningMasterMark}
              alt=""
              aria-hidden="true"
              className="h-full w-full object-contain"
            />
          </span>
          <span className="truncate text-sm font-semibold tracking-[-0.01em] text-[#202020]">
            LearningMaster
          </span>
          <ChevronRight size={13} className="ml-auto text-[#9b9a97] opacity-0 transition-opacity group-hover:opacity-100" />
        </button>
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-md text-[#8f8e8b] hover:bg-black/[0.05] hover:text-[#202020]"
            aria-label={t("nav.closeMenu")}
          >
            <X size={17} />
          </button>
        ) : null}
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-4 custom-scrollbar" aria-label={t("nav.workspace") }>
        <div className="space-y-0.5">
          <NavButton
            active={active === "home"}
            icon={Home}
            label={t("nav.home")}
            onClick={() => go("/")}
          />
          <NavButton
            icon={Plus}
            label={t("nav.newMap")}
            onClick={() => go("/")}
          />
          {isAuthenticated ? (
            <NavButton
              active={active === "learning"}
              icon={BookOpen}
              label={t("nav.myLearning")}
              onClick={() => go("/my-learning")}
            />
          ) : null}
        </div>

        {isAuthenticated && recentPlans.length > 0 ? (
          <div className="mt-7">
            <p className="mb-1 px-2.5 text-[11px] font-medium text-[#91908d]">
              {t("nav.recentPlans")}
            </p>
            <div className="space-y-0.5">
              {recentPlans.map((plan) => (
                <button
                  type="button"
                  key={plan.id}
                  onClick={() => go(`/graph/${plan.id}`)}
                  className="flex min-h-8 w-full items-center gap-2 rounded-md px-2.5 text-left text-sm text-[#6f6e6b] hover:bg-black/[0.04] hover:text-[#202020]"
                >
                  <span className="text-[13px]" aria-hidden="true">▱</span>
                  <span className="truncate" title={plan.title}>{compactPlanTitle(plan.title)}</span>
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </nav>

      <div className="space-y-2 border-t border-black/[0.07] p-3">
        <LanguageToggle className="w-full justify-center" />
        {isAuthenticated ? (
          <button
            type="button"
            onClick={handleLogout}
            className="flex min-h-9 w-full items-center gap-2.5 rounded-md px-2.5 text-sm text-[#6f6e6b] hover:bg-red-50 hover:text-red-700"
          >
            <LogOut size={15} />
            {t("nav.signOut")}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => go("/auth")}
            className="flex min-h-9 w-full items-center gap-2.5 rounded-md bg-[#202020] px-2.5 text-sm font-medium text-white hover:bg-black active:scale-[0.99]"
          >
            <LogIn size={15} />
            {t("nav.signIn")}
          </button>
        )}
      </div>
    </div>
  );
};

const WorkspaceShell = ({ active, children, contentClassName = "" }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { t } = useLanguage();

  return (
    <div className="min-h-screen bg-[var(--color-canvas)]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 border-r border-black/[0.07] lg:block">
        <SidebarContent active={active} />
      </aside>

      <header className="sticky top-0 z-30 flex h-12 items-center justify-between border-b border-black/[0.07] bg-[rgba(255,253,248,0.9)] px-3 backdrop-blur-xl lg:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="flex h-8 w-8 items-center justify-center rounded-md text-[#5f5e5b] hover:bg-black/[0.05]"
          aria-label={t("nav.openMenu")}
        >
          <Menu size={18} />
        </button>
        <span className="text-sm font-semibold text-[#202020]">LearningMaster</span>
        <span className="h-8 w-8" aria-hidden="true" />
      </header>

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/20"
            aria-label={t("nav.closeMenu")}
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-[min(19rem,88vw)] border-r border-black/10 shadow-[16px_0_48px_rgba(0,0,0,0.12)]">
            <SidebarContent
              active={active}
              onNavigate={() => setMobileOpen(false)}
              onClose={() => setMobileOpen(false)}
            />
          </aside>
        </div>
      ) : null}

      <main className={`min-h-screen lg:pl-60 ${contentClassName}`}>{children}</main>
    </div>
  );
};

export default WorkspaceShell;
