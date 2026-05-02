import { ExternalLink } from "lucide-react";
import type { Source } from "../lib/api";

type SourceNavigatorProps = {
  bestSource: Source | null;
  supportingSources: Source[];
};

export function SourceNavigator({ bestSource, supportingSources }: SourceNavigatorProps) {
  const sources = [bestSource, ...supportingSources].filter(Boolean) as Source[];
  if (sources.length === 0) {
    return null;
  }

  return (
    <section className="source-navigator" aria-labelledby="source-navigator-heading">
      <div className="panel-heading">
        <h2 id="source-navigator-heading">Source navigator</h2>
      </div>
      <ol>
        {sources.map((source, index) => (
          <li key={`${source.title}-${source.url}`}>
            <span className={index === 0 ? "source-rank source-rank-primary" : "source-rank"}>{index + 1}</span>
            <div>
              <a href={source.url} target="_blank" rel="noreferrer">
                <span>{source.title}</span>
                <ExternalLink aria-hidden="true" size={14} />
              </a>
              <p>{[source.heading_path, source.path, source.repo].filter(Boolean).join(" - ")}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
