"use client";

import React, { useEffect, useState } from "react";
import { apiBaseUrl, getJson, postJson } from "../lib/api";

type SpotifyStatus = { connected: boolean; scopes: string[]; expires_at?: string | null };

export function SpotifyConnectStatus() {
  const [status, setStatus] = useState<SpotifyStatus | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);

  useEffect(() => {
    getJson<SpotifyStatus>("/me/spotify/status")
      .then(setStatus)
      .catch(() => setStatus({ connected: false, scopes: [] }));
  }, []);

  async function syncSpotify() {
    setSyncStatus("Syncing Spotify library");
    try {
      const result = await postJson<{ counts?: Record<string, number> }>("/sync/spotify", {});
      const total = Object.values(result.counts ?? {}).reduce((sum, value) => sum + value, 0);
      setSyncStatus(`Synced ${total} items`);
    } catch {
      setSyncStatus("Sync failed. Check Spotify permissions and API logs.");
    }
  }

  return (
    <section className="border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">Spotify</h2>
      <p className="mt-2 text-sm text-slate-600">
        {status?.connected ? "Connected and ready to sync." : "Not connected yet."}
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <a href={`${apiBaseUrl}/auth/spotify/login`} className="inline-block bg-groove px-4 py-2 text-sm font-medium text-white">
          {status?.connected ? "Reconnect Spotify" : "Connect Spotify"}
        </a>
        {status?.connected ? (
          <button type="button" onClick={() => void syncSpotify()} className="border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800">
            Sync Spotify now
          </button>
        ) : null}
      </div>
      {syncStatus ? <p className="mt-2 text-sm text-slate-600">{syncStatus}</p> : null}
    </section>
  );
}
