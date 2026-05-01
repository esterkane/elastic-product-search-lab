import { ExternalLink } from "lucide-react";
import type { SearchHit } from "../lib/api";

type ResultCardProps = {
  result: SearchHit;
};

export function ResultCard({ result }: ResultCardProps) {
  const title = result.title || result.heading_path || result.path || result.id;
  const snippet = [result.heading_path, result.path, result.repo].filter(Boolean).join(" - ");
  const breakdown = result.score_breakdown;

  return (
    <article className="result-card" aria-labelledby={`result-${result.id}`}>
      <div className="result-card__header">
        <div>
          <h3 id={`result-${result.id}`}>{title}</h3>
          <p>{snippet || "Indexed repository evidence"}</p>
        </div>
        <span className="score" aria-label={`Score ${result.score.toFixed(3)}`}>
          {result.score.toFixed(3)}
        </span>
      </div>
      <div className="meta-row" aria-label="Result metadata">
        {result.content_type && <span>{result.content_type}</span>}
        {result.license_family && <span>{result.license_family}</span>}
      </div>
      {breakdown && (
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
      )}
      <a className="source-link" href={result.source_url} target="_blank" rel="noreferrer">
        <span>Open source</span>
        <ExternalLink aria-hidden="true" size={16} />
      </a>
    </article>
  );
}
