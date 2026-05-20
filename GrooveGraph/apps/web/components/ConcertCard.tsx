"use client";

import React from "react";
import type { Concert } from "../lib/api";

export function ConcertCard({ concert }: { concert: Concert }) {
  const date = concert.starts_at ? new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(concert.starts_at)) : "Date TBA";
  return (
    <article className="border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase text-slate-500">{concert.source_status}</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">{concert.title}</h2>
          <p className="mt-1 text-sm text-slate-600">{date}</p>
        </div>
        <span className="text-xs text-slate-500">{Math.round(concert.confidence * 100)}%</span>
      </div>
      <p className="mt-3 text-sm text-slate-700">
        {concert.venue?.name ?? "Venue TBA"} · {concert.city ?? concert.venue?.city ?? "City TBA"}
        {concert.country ? `, ${concert.country}` : ""}
      </p>
      {concert.lineup.length > 0 ? <p className="mt-2 text-sm text-slate-500">Lineup: {concert.lineup.join(", ")}</p> : null}
      <div className="mt-3 flex gap-3 text-sm">
        {concert.ticket_url ? <a className="text-groove hover:underline" href={concert.ticket_url}>Tickets</a> : null}
        {concert.source_url ? <a className="text-groove hover:underline" href={concert.source_url}>Source</a> : null}
      </div>
    </article>
  );
}
