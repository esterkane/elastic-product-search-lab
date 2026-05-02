import { FormEvent } from "react";
import { Loader2, Search } from "lucide-react";

type SearchBarProps = {
  query: string;
  onQueryChange: (query: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  advanced: {
    repo: string;
    path: string;
    headingPath: string;
    contentType: string;
    licenseFamily: string;
    boostDocumentation: boolean;
    explainScores: boolean;
    repos: string[];
    contentTypes: string[];
    licenseFamilies: string[];
    onRepoChange: (value: string) => void;
    onPathChange: (value: string) => void;
    onHeadingPathChange: (value: string) => void;
    onContentTypeChange: (value: string) => void;
    onLicenseFamilyChange: (value: string) => void;
    onBoostDocumentationChange: (value: boolean) => void;
    onExplainScoresChange: (value: boolean) => void;
  };
};

export function SearchBar({ query, onQueryChange, onSubmit, isLoading, advanced }: SearchBarProps) {
  return (
    <form className="search-form" onSubmit={onSubmit}>
      <div className="query-row">
        <label className="query-field">
          <span>Query</span>
          <input value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Ask a documentation question" />
        </label>
        <button type="submit" disabled={isLoading}>
          {isLoading ? <Loader2 aria-hidden="true" className="spin" size={18} /> : <Search aria-hidden="true" size={18} />}
          <span>{isLoading ? "Searching" : "Search"}</span>
        </button>
      </div>

      <details className="advanced-options">
        <summary>Advanced options</summary>
        <div className="advanced-options__content">
          <div className="filter-row">
            <label>
              <span>Repo</span>
              <select value={advanced.repo} onChange={(event) => advanced.onRepoChange(event.target.value)}>
                <option value="">All repos</option>
                {advanced.repos.map((item) => (
                  <option value={item} key={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>License</span>
              <select value={advanced.licenseFamily} onChange={(event) => advanced.onLicenseFamilyChange(event.target.value)}>
                <option value="">All licenses</option>
                {advanced.licenseFamilies.map((item) => (
                  <option value={item} key={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Content type</span>
              <select value={advanced.contentType} onChange={(event) => advanced.onContentTypeChange(event.target.value)}>
                <option value="">All types</option>
                {advanced.contentTypes.map((item) => (
                  <option value={item} key={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={advanced.explainScores}
                onChange={(event) => advanced.onExplainScoresChange(event.target.checked)}
              />
              <span>Explain scores</span>
            </label>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={advanced.boostDocumentation}
                onChange={(event) => advanced.onBoostDocumentationChange(event.target.checked)}
              />
              <span>Boost docs</span>
            </label>
          </div>

          <div className="metadata-row">
            <label>
              <span>Path</span>
              <input
                value={advanced.path}
                onChange={(event) => advanced.onPathChange(event.target.value)}
                placeholder="solutions/search/ranking/semantic-reranking.md"
              />
            </label>

            <label>
              <span>Heading</span>
              <input
                value={advanced.headingPath}
                onChange={(event) => advanced.onHeadingPathChange(event.target.value)}
                placeholder="Semantic reranking [semantic-reranking]"
              />
            </label>
          </div>
        </div>
      </details>
    </form>
  );
}
