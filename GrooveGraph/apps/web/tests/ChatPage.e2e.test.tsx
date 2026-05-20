import React from "react";
import { render, screen } from "@testing-library/react";
import ChatPage from "../app/chat/page";

describe("Chat page smoke", () => {
  it("renders the chat route with the stream input", () => {
    render(<ChatPage />);

    expect(screen.getByRole("heading", { name: "Research Chat" })).toBeInTheDocument();
    expect(screen.getByLabelText("message")).toBeInTheDocument();
    expect(screen.getByLabelText("tool calls")).toBeInTheDocument();
  });
});
