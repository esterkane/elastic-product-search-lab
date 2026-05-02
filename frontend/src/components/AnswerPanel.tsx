import type { AnswerResponse } from "../lib/api";
import { formatAnswer } from "../lib/resultFormatter";
import { AnswerSummary } from "./AnswerSummary";
import { EvidenceCard } from "./EvidenceCard";
import { QueryInsights } from "./QueryInsights";
import { SourceNavigator } from "./SourceNavigator";

type AnswerPanelProps = {
  answer: AnswerResponse | null;
  isLoading?: boolean;
};

export function AnswerPanel({ answer, isLoading = false }: AnswerPanelProps) {
  const model = formatAnswer(answer);

  return (
    <section className="answer-explorer" aria-label="Answer explorer">
      <AnswerSummary model={model} isLoading={isLoading} />

      <section className="evidence-panel" aria-labelledby="evidence-heading">
        <div className="panel-heading">
          <h2 id="evidence-heading">Evidence</h2>
        </div>
        {model.primaryEvidence ? (
          <>
            <EvidenceCard evidence={model.primaryEvidence} primary />
            {model.supportingEvidence.length > 0 && (
              <div className="supporting-evidence">
                <p className="result-group-label">More useful excerpts</p>
                {model.supportingEvidence.slice(0, 2).map((item) => (
                  <EvidenceCard evidence={item} key={`${item.title}-${item.reader_url}-${item.source_url}`} />
                ))}
              </div>
            )}
            <QueryInsights primaryTitle={model.primaryEvidence.title} />
          </>
        ) : (
          <p className="empty-state">Evidence excerpts will appear here after the answer endpoint returns grounded sources.</p>
        )}
      </section>

      <SourceNavigator bestSource={model.bestSource} supportingSources={model.supportingSources} />
    </section>
  );
}
