"use client";

import React, { useState } from "react";
import { postJson } from "../lib/api";

const actions = ["liked", "hidden", "saved", "added_to_playlist"] as const;

export function FeedbackButtons({ recommendationId }: { recommendationId: string }) {
  const [selected, setSelected] = useState<string | null>(null);

  async function submit(action: string) {
    setSelected(action);
    await postJson(`/recommendations/${recommendationId}/feedback`, { action });
  }

  return (
    <div className="flex flex-wrap gap-2" aria-label="recommendation feedback">
      {actions.map((action) => (
        <button
          key={action}
          type="button"
          onClick={() => void submit(action)}
          className={`border px-3 py-1 text-sm ${
            selected === action ? "border-groove bg-groove text-white" : "border-slate-200 bg-white text-slate-700"
          }`}
        >
          {action.replaceAll("_", " ")}
        </button>
      ))}
    </div>
  );
}
