import React from "react";
import { AppShell, PageHeader } from "../../components/AppShell";
import { SpotifyConnectStatus } from "../../components/SpotifyConnectStatus";
import { SyncStatus } from "../../components/SyncStatus";

export default function ConnectPage() {
  return (
    <AppShell>
      <PageHeader title="Connect" subtitle="Link Spotify, then sync your saved tracks, followed artists, playlists, and top listening history." />
      <div className="grid gap-4 md:grid-cols-2">
        <SpotifyConnectStatus />
        <SyncStatus />
      </div>
    </AppShell>
  );
}
