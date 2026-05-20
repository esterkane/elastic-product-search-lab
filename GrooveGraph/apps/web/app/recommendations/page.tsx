"use client";

import React, { useEffect, useState } from "react";
import { AppShell, PageHeader } from "../../components/AppShell";
import { PlaylistCreateDialog } from "../../components/PlaylistCreateDialog";
import { RecommendationCard } from "../../components/RecommendationCard";
import { getJson, postJson, type Recommendation } from "../../lib/api";

export default function RecommendationsPage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [items, setItems] = useState<Recommendation[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [status, setStatus] = useState("Loading latest recommendations");

  async function loadLatest() {
    const payload = await getJson<{ run_id: string | null; items: Recommendation[] }>("/recommendations/latest");
    setRunId(payload.run_id);
    setItems(payload.items);
    setSelectedIds([]);
    setStatus(payload.items.length ? "Ready" : "No recommendations yet");
  }

  async function runRecommendations() {
    setStatus("Scoring recommendations");
    const payload = await postJson<{ run_id: string; items: Recommendation[] }>("/recommendations/run", {
      prompt: "recommend music",
      include_concert_boost: true
    });
    setRunId(payload.run_id);
    setItems(payload.items);
    setSelectedIds([]);
    setStatus("Ready");
  }

  useEffect(() => {
    void loadLatest().catch(() => setStatus("Recommendations unavailable"));
  }, []);

  return (
    <AppShell>
      <PageHeader title="Recommendations" subtitle="Each recommendation explains the seeds, evidence, and score factors behind it." />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => void runRecommendations()} className="bg-groove px-4 py-2 text-sm font-medium text-white">
          Run recommendations
        </button>
        <p className="text-sm text-slate-500">{status}</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-4">
          {items.map((item) => (
            <RecommendationCard
              key={item.id}
              recommendation={item}
              selected={selectedIds.includes(item.id)}
              onSelectedChange={(selected) =>
                setSelectedIds((current) => selected ? [...current, item.id] : current.filter((id) => id !== item.id))
              }
            />
          ))}
        </div>
        <PlaylistCreateDialog runId={runId} recommendations={items} selectedIds={selectedIds} />
      </div>
    </AppShell>
  );
}
