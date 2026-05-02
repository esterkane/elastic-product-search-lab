import { ExternalLink } from "lucide-react";
import type { Source } from "../lib/api";
import { formatSource } from "../lib/resultFormatter";

type SourceNavigatorProps = {
  bestSource: Source | null;
  supportingSources: Source[];
};

export function SourceNavigator({ bestSource, supportingSources }: SourceNavigatorProps) {
  const sources = ([bestSource, ...supportingSources].filter(Boolean) as Source[]).map(formatSource);
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
                <span>{source.display.title}</span>
                <ExternalLink aria-hidden="true" size={14} />
              </a>
              <dl className="metadata-list metadata-list-compact">
                {source.display.section && (
                  <div>
                    <dt>Section</dt>
                    <dd>{source.display.section}</dd>
                  </div>
                )}
                {source.display.filePath && (
                  <div>
                    <dt>File</dt>
                    <dd>{source.display.filePath}</dd>
                  </div>
                )}
                {source.display.repo && (
                  <div>
                    <dt>Repo</dt>
                    <dd>{source.display.repo}</dd>
                  </div>
                )}
              </dl>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
