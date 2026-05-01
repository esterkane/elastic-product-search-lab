import { Lightbulb } from "lucide-react";
import type { Category, Recommendation } from "../lib/api";
import { SourceList } from "./SourceList";

type RecommendationPanelProps = {
  categories: Category[];
  recommendations: Recommendation[];
  selectedCategory: Category | "all";
  onCategoryChange: (category: Category | "all") => void;
};

const CATEGORY_LABELS: Record<Category, string> = {
  relevance: "Relevance",
  ingestion: "Ingestion",
  mapping: "Mapping",
  performance: "Performance",
  resiliency: "Resiliency"
};

export function RecommendationPanel({
  categories,
  recommendations,
  selectedCategory,
  onCategoryChange
}: RecommendationPanelProps) {
  const visibleRecommendations =
    selectedCategory === "all"
      ? recommendations
      : recommendations.filter((item) => item.category === selectedCategory);

  return (
    <section className="panel" aria-labelledby="recommendations-heading">
      <div className="panel-heading">
        <Lightbulb aria-hidden="true" size={18} />
        <h2 id="recommendations-heading">Improvement Suggestions</h2>
      </div>

      <div className="segmented-control" aria-label="Recommendation category">
        <button
          type="button"
          className={selectedCategory === "all" ? "active" : ""}
          onClick={() => onCategoryChange("all")}
        >
          All
        </button>
        {categories.map((category) => (
          <button
            type="button"
            key={category}
            className={selectedCategory === category ? "active" : ""}
            onClick={() => onCategoryChange(category)}
          >
            {CATEGORY_LABELS[category]}
          </button>
        ))}
      </div>

      {visibleRecommendations.length === 0 ? (
        <p className="empty-state">Run an analysis to see recommendations.</p>
      ) : (
        <div className="recommendation-stack">
          {visibleRecommendations.map((item) => (
            <article className="recommendation" key={item.category}>
              <h3>{CATEGORY_LABELS[item.category]}</h3>
              <p>{item.recommendation}</p>
              <SourceList sources={item.evidence} />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
