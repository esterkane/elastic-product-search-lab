import { FormEvent } from "react";
import { Loader2, Search } from "lucide-react";
import type { ChangeTopic, TimeRange } from "../lib/api";

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
    topic: ChangeTopic | "";
    versionFrom: string;
    versionTo: string;
    timeRange: TimeRange;
    boostDocumentation: boolean;
    explainScores: boolean;
    repos: string[];
    contentTypes: string[];
    licenseFamilies: string[];
    topics: { value: ChangeTopic; label: string }[];
    versions: string[];
    timeRanges: { value: TimeRange; label: string }[];
    onRepoChange: (value: string) => void;
    onPathChange: (value: string) => void;
    onHeadingPathChange: (value: string) => void;
    onContentTypeChange: (value: string) => void;
    onLicenseFamilyChange: (value: string) => void;
    onTopicChange: (value: ChangeTopic | "") => void;
    onVersionFromChange: (value: string) => void;
    onVersionToChange: (value: string) => void;
    onTimeRangeChange: (value: TimeRange) => void;
    onBoostDocumentationChange: (value: boolean) => void;
    onExplainScoresChange: (value: boolean) => void;
  };
};

export function SearchBar({ query, onQueryChange, onSubmit, isLoading, advanced }: SearchBarProps) {
  return (
    <form className="search-form" onSubmit={onSubmit}>
      <div className="query-row">
        <label className="query-field">
          <span>Release question</span>
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Ask what changed in Elasticsearch 8.x or 9.x"
          />
        </label>
        <button type="submit" disabled={isLoading}>
          {isLoading ? <Loader2 aria-hidden="true" className="spin" size={18} /> : <Search aria-hidden="true" size={18} />}
          <span>{isLoading ? "Searching" : "Search"}</span>
        </button>
      </div>

      <div className="release-row" aria-label="Release intelligence filters">
        <label>
          <span>Topic</span>
          <select value={advanced.topic} onChange={(event) => advanced.onTopicChange(event.target.value as ChangeTopic | "")}>
            <option value="">All topics</option>
            {advanced.topics.map((item) => (
              <option value={item.value} key={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Version from</span>
          <input
            list="version-options"
            value={advanced.versionFrom}
            onChange={(event) => advanced.onVersionFromChange(event.target.value)}
            placeholder="8.0"
          />
        </label>

        <label>
          <span>Version to</span>
          <input
            list="version-options"
            value={advanced.versionTo}
            onChange={(event) => advanced.onVersionToChange(event.target.value)}
            placeholder="Latest"
          />
        </label>

        <label>
          <span>Time range</span>
          <select value={advanced.timeRange} onChange={(event) => advanced.onTimeRangeChange(event.target.value as TimeRange)}>
            {advanced.timeRanges.map((item) => (
              <option value={item.value} key={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="source-filter-row">
        <label>
          <span>Repo filter</span>
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
          <span>Content type filter</span>
          <select value={advanced.contentType} onChange={(event) => advanced.onContentTypeChange(event.target.value)}>
            <option value="">All types</option>
            {advanced.contentTypes.map((item) => (
              <option value={item} key={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>
      <datalist id="version-options">
        {advanced.versions.map((item) => (
          <option value={item} key={item} />
        ))}
      </datalist>

      <details className="advanced-options">
        <summary>Secondary filters</summary>
        <div className="advanced-options__content">
          <div className="filter-row">
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
