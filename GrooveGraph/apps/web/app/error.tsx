"use client";

import React from "react";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main className="min-h-screen bg-stone-50 p-6 text-slate-950">
      <section className="mx-auto max-w-xl border border-slate-200 bg-white p-5">
        <h1 className="text-xl font-semibold">Something went wrong</h1>
        <p className="mt-2 text-sm text-slate-600">{error.message || "The page could not be rendered."}</p>
        <button type="button" onClick={reset} className="mt-4 bg-slate-950 px-4 py-2 text-sm text-white">
          Try again
        </button>
      </section>
    </main>
  );
}
