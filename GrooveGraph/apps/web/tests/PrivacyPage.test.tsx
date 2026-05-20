import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import PrivacyPage from "../app/settings/privacy/page";

describe("PrivacyPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows stored data rules and Spotify status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ connected: true, scopes: ["user-library-read"] })
      })
    );

    render(<PrivacyPage />);

    expect(screen.getByText(/does not train ML or AI models/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Spotify is connected.")).toBeInTheDocument();
    });
  });

  it("shows useful state after disconnect", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({ ok: true, json: async () => ({ connected: true, scopes: [] }) })
        .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "disconnected" }) })
    );

    render(<PrivacyPage />);
    fireEvent.click(screen.getByRole("button", { name: "Disconnect Spotify" }));

    await waitFor(() => {
      expect(screen.getByText("Spotify disconnected and linked Spotify data removed.")).toBeInTheDocument();
    });
  });
});
