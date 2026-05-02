import { ExternalLink } from "lucide-react";
import type { FormattedEvidence } from "../lib/resultFormatter";
import { SourceMetadata } from "./SourceMetadata";

type EvidenceCardProps = {
  evidence: FormattedEvidence;
  primary?: boolean;
};

export function EvidenceCard({ evidence, primary = false }: EvidenceCardProps) {
  return (
    <article className={`evidence-card ${primary ? "evidence-card-primary" : ""}`}>
      <div className="evidence-card__header">
        <div>
          <p className="evidence-kicker">{primary ? "Best excerpt" : "Useful excerpt"}</p>
          <h3>{evidence.title}</h3>
          <p className="evidence-concept">{evidence.concept}</p>
          <SourceMetadata display={evidence.display} />
        </div>
      </div>
      <div className="tag-row">
        {evidence.tags.map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
      <p className="evidence-claim">{evidence.takeaway}</p>
      <p className="look-for-note">{evidence.whatToLookFor}</p>
      <blockquote className="evidence-snippet">{renderHighlightedText(evidence.excerpt, evidence.highlight_terms)}</blockquote>
      <div className="answer-evidence__links">
        <a className="evidence-cta evidence-cta-primary" href={evidence.reader_url} target="_blank" rel="noreferrer">
          <span>{evidence.link_label === "Read documentation" ? "Read docs" : "Open source"}</span>
          <ExternalLink aria-hidden="true" size={15} />
        </a>
        {evidence.reader_url !== evidence.source_url && (
          <a className="evidence-cta" href={evidence.source_url} target="_blank" rel="noreferrer">
            <span>Open source</span>
            <ExternalLink aria-hidden="true" size={15} />
          </a>
        )}
      </div>
    </article>
  );
}

function renderHighlightedText(text: string, highlights: string[]) {
  const escaped = Array.from(new Set(highlights.map((term) => term.trim()).filter(Boolean))).map(escapeRegExp);
  if (escaped.length === 0) {
    return text;
  }

  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  return text.split(pattern).map((part, index) => {
    const isHighlight = highlights.some((term) => term.toLowerCase() === part.toLowerCase());
    return isHighlight ? <mark key={`${part}-${index}`}>{part}</mark> : part;
  });
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
