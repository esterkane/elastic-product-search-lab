import type { SearchHit } from "../lib/api";
import { groupRelatedResults } from "../lib/resultFormatter";
import { ResultCard } from "./ResultCard";

type ResultListProps = {
  hits: SearchHit[];
};

export function ResultList({ hits }: ResultListProps) {
  const grouped = groupRelatedResults(hits);

  if (!grouped.primary) {
    return <p className="empty-state">Run a search to see release sources.</p>;
  }

  return (
    <div className="result-stack">
      <div>
        <p className="result-group-label">Best source candidate</p>
        <ResultCard result={grouped.primary} />
      </div>
      {grouped.related.length > 0 && (
        <details className="related-results" open={grouped.related.length <= 3}>
          <summary>Related sources ({grouped.related.length})</summary>
          <div className="result-stack">
            {grouped.related.map((result) => (
              <ResultCard key={result.id} result={result} />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
