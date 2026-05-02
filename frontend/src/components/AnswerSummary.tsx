import { ArrowRight, MapPin } from "lucide-react";
import type { AnswerViewModel } from "../lib/resultFormatter";
import { ConfidenceBadge } from "./ConfidenceBadge";

type AnswerSummaryProps = {
  model: AnswerViewModel;
  isLoading?: boolean;
};

export function AnswerSummary({ model, isLoading = false }: AnswerSummaryProps) {
  return (
    <section className="answer-summary-panel" aria-labelledby="answer-heading">
      <div className="answer-summary-panel__top">
        <div>
          <p className="eyebrow">Start here</p>
          <h2 id="answer-heading">Answer</h2>
        </div>
        <ConfidenceBadge confidence={model.confidence} />
      </div>
      <p className="answer-summary">
        {isLoading ? "Building a grounded answer from the strongest evidence." : model.directAnswer}
      </p>
      {model.whatNew && (
        <div className="insight-block insight-block-new">
          <h3>What&apos;s new</h3>
          <p>{model.whatNew}</p>
        </div>
      )}
      <div className="insight-grid">
        <div className="insight-block">
          <h3>Why it matters</h3>
          <p>{model.important}</p>
        </div>
        {model.bestSource && (
          <div className="insight-block">
            <h3>Where to read next</h3>
            <p>{[model.bestSource.heading_path, model.bestSource.path, model.bestSource.repo].filter(Boolean).join(" - ")}</p>
            <a className="best-link" href={model.bestSource.url} target="_blank" rel="noreferrer">
              <MapPin aria-hidden="true" size={15} />
              <span>{model.bestSource.link_label ?? "Open source"}</span>
              <ArrowRight aria-hidden="true" size={15} />
            </a>
          </div>
        )}
      </div>
    </section>
  );
}
