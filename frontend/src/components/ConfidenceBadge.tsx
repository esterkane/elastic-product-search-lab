import type { ConfidenceLevel } from "../lib/resultFormatter";

type ConfidenceBadgeProps = {
  confidence: ConfidenceLevel;
};

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  return <span className={`confidence-badge confidence-badge-${confidence}`}>{confidence} confidence</span>;
}
