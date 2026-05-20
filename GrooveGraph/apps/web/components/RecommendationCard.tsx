"use client";

import React from "react";
import type { Recommendation } from "../lib/api";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { FeedbackButtons } from "./FeedbackButtons";

export function RecommendationCard({
  recommendation,
  selected = false,
  onSelectedChange
}: {
  recommendation: Recommendation;
  selected?: boolean;
  onSelectedChange?: (selected: boolean) => void;
}) {
  return (
    <article className="border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex gap-3">
          {onSelectedChange ? (
            <input
              type="checkbox"
              checked={selected}
              onChange={(event) => onSelectedChange(event.target.checked)}
              className="mt-2 h-4 w-4"
              aria-label={`select ${recommendation.name ?? "recommendation"}`}
            />
          ) : null}
          <div>
          <p className="text-xs uppercase text-slate-500">{recommendation.type}</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">{recommendation.name ?? "Recommendation"}</h2>
          {recommendation.artist_name ? <p className="text-sm text-slate-600">{recommendation.artist_name}</p> : null}
          </div>
        </div>
        <span className="border border-groove px-2 py-1 text-xs font-medium text-groove">
          {Math.round(recommendation.confidence * 100)}%
        </span>
      </div>
      <section className="mt-4">
        <h3 className="text-sm font-semibold text-slate-900">Why this was recommended</h3>
        <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-700">
          {recommendation.reason_bullets.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
        <p className="mt-2 text-sm text-slate-500">{recommendation.seed_explanation}</p>
      </section>
      <div className="mt-4">
        <FeedbackButtons recommendationId={recommendation.id} />
      </div>
      <div className="mt-4">
        <EvidenceDrawer citations={recommendation.source_evidence} />
      </div>
    </article>
  );
}
