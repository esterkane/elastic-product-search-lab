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
        Start with <strong>{primaryTitle}</strong>. Use it to understand the main idea, then scan the other excerpts only
        for caveats, examples, or implementation details.
      </p>
    </aside>
  );
}
