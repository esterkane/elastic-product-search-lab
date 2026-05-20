import React from "react";
import { AppShell, PageHeader } from "../../components/AppShell";
import { ArtistConnectionGraph } from "../../components/ArtistConnectionGraph";

export default function GraphPage() {
  return (
    <AppShell>
      <PageHeader title="Graph" subtitle="Explore artist, band, collaborator, side-project, and source-backed relationships." />
      <ArtistConnectionGraph
        nodes={[
          { id: "radiohead", label: "Radiohead" },
          { id: "the-smile", label: "The Smile", group: "project" },
          { id: "thom-yorke", label: "Thom Yorke" },
          { id: "pixies", label: "Pixies" }
        ]}
        links={[
          { source: "the-smile", target: "radiohead", label: "SIDE_PROJECT_OF" },
          { source: "thom-yorke", target: "radiohead", label: "MEMBER_OF" },
          { source: "thom-yorke", target: "pixies", label: "INFLUENCED_BY" }
        ]}
      />
    </AppShell>
  );
}
