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
      <div className="explain-block">
        <h3>Explain this result</h3>
        <p>{model.explanation}</p>
      </div>
      {model.whatNew.length > 0 && (
        <div className="insight-block insight-block-new">
          <h3>What&apos;s new</h3>
          <ul>
            {model.whatNew.slice(0, 4).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="insight-grid">
        <div className="insight-block">
          <h3>Why it matters</h3>
          <p>{model.important}</p>
        </div>
        <div className="insight-block">
          <h3>Key takeaways</h3>
          <ul>
            {model.keyTakeaways.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        {model.bestSource && (
          <div className="insight-block">
            <h3>Where to read next</h3>
            <dl className="metadata-list">
              <div>
                <dt>Source</dt>
                <dd>{model.bestSource.display.title}</dd>
              </div>
              {model.bestSource.display.section && (
                <div>
                  <dt>Section</dt>
                  <dd>{model.bestSource.display.section}</dd>
                </div>
              )}
              {model.bestSource.display.filePath && (
                <div>
                  <dt>File</dt>
                  <dd>{model.bestSource.display.filePath}</dd>
                </div>
              )}
              {model.bestSource.display.repo && (
                <div>
                  <dt>Repo</dt>
                  <dd>{model.bestSource.display.repo}</dd>
                </div>
              )}
            </dl>
            <a className="best-link" href={model.bestSource.url} target="_blank" rel="noreferrer">
              <MapPin aria-hidden="true" size={15} />
              <span>{model.bestSource.link_label === "Read documentation" ? "Read docs" : "Open source"}</span>
              <ArrowRight aria-hidden="true" size={15} />
            </a>
          </div>
        )}
      </div>
    </section>
  );
}
