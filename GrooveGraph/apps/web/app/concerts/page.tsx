"use client";

import React, { useState } from "react";
import { AppShell, PageHeader } from "../../components/AppShell";
import { ConcertCard } from "../../components/ConcertCard";
import { getJson, type Concert } from "../../lib/api";

export default function ConcertsPage() {
  const [city, setCity] = useState("Berlin");
  const [items, setItems] = useState<Concert[]>([]);
  const [status, setStatus] = useState("Search nearby concerts or generate recommendations from your music profile.");

  async function search() {
    setStatus("Searching concerts");
    try {
      const payload = await getJson<{ items: Concert[] }>(`/concerts/nearby?city=${encodeURIComponent(city)}&radius_km=50`);
      setItems(payload.items);
      setStatus(payload.items.length ? "Ready" : "No concerts found");
    } catch {
      setStatus("Concert search unavailable");
    }
  }

  return (
    <AppShell>
      <PageHeader title="Concerts" subtitle="Upcoming and historical live-performance context with source links and confidence." />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <input value={city} onChange={(event) => setCity(event.target.value)} className="border border-slate-300 px-3 py-2 text-sm" aria-label="city" />
        <button type="button" onClick={() => void search()} className="bg-groove px-4 py-2 text-sm font-medium text-white">
          Search nearby
        </button>
      </div>
      <p className="mb-4 text-sm text-slate-500">{status}</p>
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((concert) => <ConcertCard key={concert.id} concert={concert} />)}
      </div>
    </AppShell>
  );
}
