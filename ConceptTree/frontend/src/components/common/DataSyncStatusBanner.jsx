import React from "react";
import { AlertCircle } from "lucide-react";
import { useAppContext } from "../../contexts/AppContext";

export default function DataSyncStatusBanner() {
  const { dataSyncStatus } = useAppContext();

  if (!dataSyncStatus?.degraded) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed left-1/2 top-3 z-[80] flex max-w-[calc(100vw-24px)] -translate-x-1/2 items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-xs font-medium text-amber-800 shadow-sm"
    >
      <AlertCircle size={14} aria-hidden="true" />
      <span className="truncate">{dataSyncStatus.message}</span>
    </div>
  );
}
