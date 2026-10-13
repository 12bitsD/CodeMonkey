import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

import AdminAccessGate from "./AdminAccessGate";
import AdminShell from "./AdminShell";
import AiUsagePanel from "./AiUsagePanel";
import OverviewPanel from "./OverviewPanel";
import SessionsPanel from "./SessionsPanel";
import SystemPanel from "./SystemPanel";
import UsersPanel from "./UsersPanel";

const sections = {
  overview: OverviewPanel,
  users: UsersPanel,
  sessions: SessionsPanel,
  "ai-usage": AiUsagePanel,
  system: SystemPanel,
};

export default function AdminPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const requestedSection = location.pathname.split("/")[2] || "overview";
  const active = sections[requestedSection] ? requestedSection : "overview";
  const ActivePanel = sections[active];

  return (
    <AdminAccessGate>
      {({ lock }) => (
        <AdminShell
          active={active}
          onNavigate={(section) => navigate(`/admin/${section}`)}
          onLock={lock}
        >
          <ActivePanel />
        </AdminShell>
      )}
    </AdminAccessGate>
  );
}
