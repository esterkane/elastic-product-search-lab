import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PlaylistCreateDialog } from "../components/PlaylistCreateDialog";

describe("PlaylistCreateDialog", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a useful error state when Spotify creation fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403, json: async () => ({}) }));

    render(
      <PlaylistCreateDialog
        runId="run-1"
        recommendations={[
          {
            id: "rec-1",
            type: "track",
            name: "Track",
            score: 0.8,
            confidence: 0.8,
            reason_bullets: ["Seed match"],
            source_evidence: [],
            seed_explanation: "From saved tracks",
            actions: []
          }
        ]}
        selectedIds={["rec-1"]}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Create discovery playlist" }));

    await waitFor(() => {
      expect(screen.getByText("Could not create playlist. Check Spotify connection and playlist permissions.")).toBeInTheDocument();
    });
  });

  it("explains artist-only runs cannot create track playlists", async () => {
    render(<PlaylistCreateDialog runId="run-1" selectedIds={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Create discovery playlist" }));

    expect(
      screen.getByText("This run only has artist recommendations. Run sync/recommendations again after Spotify has saved tracks or playlist tracks.")
    ).toBeInTheDocument();
  });
});
