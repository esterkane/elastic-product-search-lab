import { ExternalLink } from "lucide-react";
import type { SearchHit } from "../lib/api";

type ResultCardProps = {
  result: SearchHit;
};

export function ResultCard({ result }: ResultCardProps) {
  const title = result.title || result.heading_path || result.path || result.id;
  const heading = result.heading_path && result.heading_path !== result.title ? result.heading_path : null;
  const location = [heading, result.path, result.repo].filter(Boolean).join(" - ");
  const breakdown = result.score_breakdown;

  return (
    <article className="result-card" aria-labelledby={`result-${result.id}`}>
      <div className="result-card__header">
        <div>
          <h3 id={`result-${result.id}`}>{title}</h3>
          <p className="result-location">{location || "Indexed repository evidence"}</p>
        </div>
        <span className="score" aria-label={`Search score ${result.score.toFixed(3)}`}>
          score {result.score.toFixed(3)}
        </span>
      </div>
      <div className="meta-row" aria-label="Result metadata">
        {result.content_type && <span>{result.content_type}</span>}
        {result.license_family && <span>{result.license_family}</span>}
      </div>
      {result.snippet && (
        <blockquote className="evidence-snippet">
          {renderHighlightedSnippet(result.snippet, result.highlights ?? [])}
        </blockquote>
      )}
      {result.match_reason && <p className="match-reason">{result.match_reason}</p>}
      {breakdown && (
        <details className="score-details">
          <summary>Show scoring details</summary>
          <dl className="score-breakdown" aria-label="Score breakdown">
            <div>
              <dt>bm25</dt>
              <dd>{breakdown.bm25.toFixed(3)}</dd>
            </div>
            <div>
              <dt>semantic</dt>
              <dd>{breakdown.semantic.toFixed(3)}</dd>
            </div>
            <div>
              <dt>fusion</dt>
              <dd>{breakdown.fusion.toFixed(3)}</dd>
            </div>
            <div>
              <dt>rerank</dt>
              <dd>{breakdown.rerank == null ? "skipped" : breakdown.rerank.toFixed(3)}</dd>
            </div>
            <div>
              <dt>final rank</dt>
              <dd>{breakdown.final_rank}</dd>
            </div>
          </dl>
        </details>
      )}
      <a className="source-link" href={result.source_url} target="_blank" rel="noreferrer">
        <span>Open source</span>
        <ExternalLink aria-hidden="true" size={16} />
      </a>
    </article>
  );
}

function renderHighlightedSnippet(snippet: string, highlights: string[]) {
  if (highlights.length === 0) {
    return snippet;
  }

  const escaped = highlights.map(escapeRegExp).filter(Boolean);
  if (escaped.length === 0) {
    return snippet;
  }

  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  return snippet.split(pattern).map((part, index) => {
    const isHighlight = highlights.some((term) => term.toLowerCase() === part.toLowerCase());
    return isHighlight ? <mark key={`${part}-${index}`}>{part}</mark> : part;
  });
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
