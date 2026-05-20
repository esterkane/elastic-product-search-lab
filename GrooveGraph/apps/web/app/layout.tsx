import type { Metadata } from "next";
import React from "react";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "GrooveGraph",
  description: "Personal music discovery and band research assistant"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
