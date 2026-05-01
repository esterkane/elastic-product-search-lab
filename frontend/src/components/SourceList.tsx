import { ExternalLink } from "lucide-react";
import type { Source } from "../lib/api";

type SourceListProps = {
  sources: Source[];
};

export function SourceList({ sources }: SourceListProps) {
  if (sources.length === 0) {
    return <p className="empty-state">No source attributions yet.</p>;
  }

  return (
    <ul className="source-list" aria-label="Source attributions">
      {sources.map((source) => (
        <li key={`${source.title}-${source.url}`}>
          <a href={source.url} target="_blank" rel="noreferrer">
            <span>{source.title}</span>
            <ExternalLink aria-hidden="true" size={15} />
          </a>
        </li>
      ))}
    </ul>
  );
}
