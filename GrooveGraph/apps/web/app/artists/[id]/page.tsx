import React from "react";
import { AppShell, PageHeader } from "../../../components/AppShell";
import { ArtistConnectionGraph } from "../../../components/ArtistConnectionGraph";
import { ConcertCard } from "../../../components/ConcertCard";
import { getJson, type Concert } from "../../../lib/api";

export default async function ArtistPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let concerts: Concert[] = [];
  try {
    concerts = (await getJson<{ items: Concert[] }>(`/artists/${encodeURIComponent(id)}/concerts`)).items;
  } catch {
    concerts = [];
  }
  return (
    <AppShell>
      <PageHeader title={`Artist ${id}`} subtitle="Live dates, setlist history, and graph connections for this artist." />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <ArtistConnectionGraph
          nodes={[
            { id, label: id },
            { id: "side-projects", label: "Side projects", group: "project" },
            { id: "collaborators", label: "Collaborators" }
          ]}
          links={[
            { source: id, target: "side-projects", label: "SIDE_PROJECT_OF" },
            { source: id, target: "collaborators", label: "COLLABORATED_WITH" }
          ]}
        />
        <section className="space-y-3">
          {concerts.length === 0 ? <p className="border border-slate-200 bg-white p-4 text-sm text-slate-500">No upcoming concerts found.</p> : null}
          {concerts.map((concert) => <ConcertCard key={concert.id} concert={concert} />)}
        </section>
      </div>
    </AppShell>
  );
}
