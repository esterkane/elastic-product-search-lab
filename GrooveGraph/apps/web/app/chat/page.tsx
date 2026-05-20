import React from "react";
import { AppShell, PageHeader } from "../../components/AppShell";
import { ChatPanel } from "../../components/ChatPanel";

export default function ChatPage() {
  return (
    <AppShell>
      <PageHeader
        title="Research Chat"
        subtitle="Ask for band history, side projects, lyrics context, concerts, collaborations, or connections. Claims are meant to carry citations."
      />
      <ChatPanel />
    </AppShell>
  );
}
