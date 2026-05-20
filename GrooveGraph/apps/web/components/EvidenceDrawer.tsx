"use client";

import React from "react";
import type { Citation } from "../lib/api";

export function EvidenceDrawer({ citations, open = true }: { citations: Citation[]; open?: boolean }) {
  if (!open) {
    return null;
  }
  return (
    <section className="border border-slate-200 bg-white p-4" aria-label="evidence">
      <h2 className="text-sm font-semibold text-slate-900">Evidence</h2>
      <div className="mt-3 space-y-3">
        {citations.length === 0 ? <p className="text-sm text-slate-500">No citations yet.</p> : null}
        {citations.map((citation, index) => (
          <article key={`${citation.url ?? citation.source_id ?? index}`} className="border-t border-slate-100 pt-3">
            <a href={citation.url ?? "#"} className="text-sm font-medium text-groove hover:underline">
              {citation.title ?? citation.url ?? citation.source_id ?? `Citation ${index + 1}`}
            </a>
            {citation.quote ? <p className="mt-1 text-sm leading-6 text-slate-600">{citation.quote}</p> : null}
          </article>
        ))}
      </div>
    </section>
  );
}
