import Link from "next/link";
import React from "react";
import type { ReactNode } from "react";

const links = [
  ["/dashboard", "Dashboard"],
  ["/chat", "Chat"],
  ["/recommendations", "Recommendations"],
  ["/graph", "Graph"],
  ["/concerts", "Concerts"],
  ["/settings/privacy", "Privacy"]
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-screen bg-stone-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <Link href="/" className="text-lg font-semibold text-groove">
            GrooveGraph
          </Link>
          <nav className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
            {links.map(([href, label]) => (
              <Link key={href} href={href} className="px-2 py-1 hover:text-slate-950">
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-5 py-6">{children}</div>
    </main>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-3xl font-semibold text-slate-950">{title}</h1>
      {subtitle ? <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{subtitle}</p> : null}
    </div>
  );
}
