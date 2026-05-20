"use client";

import React, { useEffect, useState } from "react";
import { AppShell, PageHeader } from "../../../components/AppShell";
import { getJson, postJson } from "../../../lib/api";

type SpotifyStatus = { connected: boolean; scopes: string[]; expires_at?: string | null };

export default function PrivacyPage() {
  const [spotify, setSpotify] = useState<SpotifyStatus | null>(null);
  const [status, setStatus] = useState("Privacy controls ready.");

  useEffect(() => {
    getJson<SpotifyStatus>("/me/spotify/status")
      .then(setSpotify)
      .catch(() => setSpotify({ connected: false, scopes: [] }));
  }, []);

  async function exportData() {
    try {
      const data = await getJson<Record<string, unknown>>("/privacy/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "groovegraph-privacy-export.json";
      anchor.click();
      URL.revokeObjectURL(url);
      setStatus("Export prepared as JSON.");
    } catch {
      setStatus("Export failed. Try again after the API is reachable.");
    }
  }

  async function disconnect() {
    try {
      await postJson("/auth/spotify/disconnect", {});
      setSpotify({ connected: false, scopes: [] });
      setStatus("Spotify disconnected and linked Spotify data removed.");
    } catch {
      setStatus("Could not disconnect Spotify.");
    }
  }

  async function deleteData() {
    const confirmed = window.confirm("Delete all personal GrooveGraph data for this user?");
    if (!confirmed) {
      return;
    }
    try {
      await postJson("/privacy/delete-my-data", {});
      setSpotify({ connected: false, scopes: [] });
      setStatus("Personal data deleted.");
    } catch {
      setStatus("Could not delete personal data.");
    }
  }

  return (
    <AppShell>
      <PageHeader title="Privacy" subtitle="Control personal music data, OAuth connections, recommendation history, and exports." />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section className="border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">What GrooveGraph Stores</h2>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
            <li>Spotify data is stored only as needed to operate recommendations, sync status, playlists, and music profile views.</li>
            <li>GrooveGraph does not train ML or AI models on Spotify content.</li>
            <li>Full lyrics are not stored unless a licensed provider and plan permits it.</li>
            <li>Web research claims keep source provenance and citations.</li>
            <li>OAuth tokens are encrypted at rest and omitted from privacy exports.</li>
            <li>Raw access and refresh tokens are redacted from logs.</li>
          </ul>
        </section>
        <section className="border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">Spotify Account</h2>
          <p className="mt-2 text-sm text-slate-600">
            {spotify?.connected ? "Spotify is connected." : "Spotify is not connected."}
          </p>
          {spotify?.scopes.length ? <p className="mt-2 text-xs text-slate-500">Scopes: {spotify.scopes.join(", ")}</p> : null}
          <div className="mt-4 grid gap-2">
            <button type="button" onClick={() => void exportData()} className="border border-slate-300 bg-white px-4 py-2 text-sm text-slate-800">
              Export as JSON
            </button>
            <button type="button" onClick={() => void disconnect()} className="border border-slate-300 bg-white px-4 py-2 text-sm text-slate-800">
              Disconnect Spotify
            </button>
            <button type="button" onClick={() => void deleteData()} className="bg-pulse px-4 py-2 text-sm font-medium text-white">
              Delete all personal data
            </button>
          </div>
          <p className="mt-4 text-sm text-slate-600" aria-live="polite">{status}</p>
        </section>
      </div>
    </AppShell>
  );
}
