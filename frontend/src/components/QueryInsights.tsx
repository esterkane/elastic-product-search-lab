import { Lightbulb } from "lucide-react";

type QueryInsightsProps = {
  primaryTitle?: string;
};

export function QueryInsights({ primaryTitle }: QueryInsightsProps) {
  if (!primaryTitle) {
    return null;
  }

  return (
    <aside className="answer-tip" aria-label="Evidence reading tip">
      <Lightbulb aria-hidden="true" size={17} />
      <p>
        Start with <strong>{primaryTitle}</strong>. It is the primary proof; supporting evidence and source navigation
        stay separate so you can verify without rereading the same claim.
      </p>
    </aside>
  );
}
