"use client";

import React, { useState } from "react";
import { postJson } from "../lib/api";
import type { Recommendation } from "../lib/api";

export function PlaylistCreateDialog({
  runId,
  recommendations = [],
  selectedIds = []
}: {
  runId: string | null;
  recommendations?: Recommendation[];
  selectedIds?: string[];
}) {
  const [name, setName] = useState("GrooveGraph Recommendations");
  const [status, setStatus] = useState<string | null>(null);
  const [spotifyUrl, setSpotifyUrl] = useState<string | null>(null);
  const trackRecommendations = recommendations.filter((item) => item.type === "track");
  const selectedTrackIds = selectedIds.filter((id) => trackRecommendations.some((item) => item.id === id));

  async function createPlaylist() {
    if (!runId) {
      setStatus("Run recommendations first.");
      return;
    }
    if (trackRecommendations.length === 0) {
      setStatus("This run only has artist recommendations. Run sync/recommendations again after Spotify has saved tracks or playlist tracks.");
      return;
    }
    try {
      const result = await postJson<{ added_tracks: number; skipped_tracks: number; external_url?: string }>(
        "/spotify/playlists/create-from-recommendations",
        { name, run_id: runId, candidate_ids: selectedTrackIds.length ? selectedTrackIds : undefined }
      );
      setSpotifyUrl(result.external_url ?? null);
      setStatus(`Playlist created with ${result.added_tracks} tracks. ${result.skipped_tracks} skipped.`);
    } catch {
      setStatus("Could not create playlist. Check Spotify connection and playlist permissions.");
      setSpotifyUrl(null);
    }
  }

  return (
    <section className="border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">Playlist Actions</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Create a new Spotify playlist from track recommendations. Artist-only recommendations cannot be added until GrooveGraph has matched them to Spotify tracks.
      </p>
      <p className="mt-2 text-xs text-slate-500">
        {trackRecommendations.length} track recommendations available. {selectedTrackIds.length || trackRecommendations.length} will be used.
      </p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="min-w-0 flex-1 border border-slate-300 px-3 py-2 text-sm"
          aria-label="playlist name"
        />
        <button type="button" onClick={() => void createPlaylist()} className="bg-slate-950 px-4 py-2 text-sm text-white">
          Create discovery playlist
        </button>
      </div>
      {status ? <p className="mt-2 text-sm text-slate-600">{status}</p> : null}
      {spotifyUrl ? (
        <a href={spotifyUrl} className="mt-2 inline-block text-sm text-groove hover:underline">
          Open in Spotify
        </a>
      ) : null}
    </section>
  );
}
