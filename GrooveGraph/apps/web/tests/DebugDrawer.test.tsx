import React from "react";
import { render, screen } from "@testing-library/react";
import { DebugDrawer } from "../components/DebugDrawer";

describe("DebugDrawer", () => {
  it("renders run/debug information outside production", () => {
    render(<DebugDrawer data={{ run_id: "run-1", tool_calls: ["web_research"] }} />);

    expect(screen.getByText("Run Debug")).toBeInTheDocument();
    expect(screen.getByText(/run-1/)).toBeInTheDocument();
  });
});
