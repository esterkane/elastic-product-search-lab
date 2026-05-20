"use client";

import React, { useState } from "react";
import { postJson } from "../lib/api";

export function SyncStatus() {
  const [status, setStatus] = useState("Idle");
  const [lastRun, setLastRun] = useState<Record<string, number> | null>(null);

  async function sync() {
    setStatus("Syncing");
    try {
      const result = await postJson<{ counts?: Record<string, number> }>("/sync/spotify", {});
      setLastRun(result.counts ?? null);
      setStatus(`Synced ${Object.values(result.counts ?? {}).reduce((sum, value) => sum + value, 0)} items`);
    } catch {
      setStatus("Sync unavailable");
    }
  }

  return (
    <section className="border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">Library Sync</h2>
      <p className="mt-2 text-sm text-slate-600">{status}</p>
      {lastRun ? <pre className="mt-2 overflow-auto bg-slate-50 p-2 text-xs text-slate-600">{JSON.stringify(lastRun, null, 2)}</pre> : null}
      <button type="button" onClick={() => void sync()} className="mt-4 bg-slate-950 px-4 py-2 text-sm font-medium text-white">
        Sync now
      </button>
    </section>
  );
}
