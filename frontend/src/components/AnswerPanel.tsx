import { BookOpen, ExternalLink, Lightbulb } from "lucide-react";
import type { AnswerResponse, Source } from "../lib/api";

type AnswerPanelProps = {
  answer: AnswerResponse | null;
  isLoading?: boolean;
};

export function AnswerPanel({ answer, isLoading = false }: AnswerPanelProps) {
  const evidence = answer?.evidence ?? [];
  const links = importantLinks(answer);

  return (
    <section className="panel answer-panel answer-panel-primary" aria-labelledby="answer-heading">
      <div className="panel-heading">
        <BookOpen aria-hidden="true" size={18} />
        <h2 id="answer-heading">Answer With Evidence</h2>
      </div>

      <p className="answer-summary">
        {answer?.summary ??
          (isLoading
            ? "Building a grounded answer from the strongest evidence."
            : "Run a search to see one clear answer with highlighted proof.")}
      </p>

      {evidence.length > 0 ? (
        <>
          <div className="answer-evidence" aria-label="Highlighted evidence">
            {evidence.slice(0, 3).map((item) => (
              <article className="answer-evidence__item" key={`${item.title}-${item.reader_url}-${item.source_url}`}>
                <div className="answer-evidence__header">
                  <h3>{item.title}</h3>
                  <p className="result-location">
                    {[item.heading_path, item.path, item.repo].filter(Boolean).join(" - ")}
                  </p>
                </div>
                <blockquote className="evidence-snippet">
                  {renderHighlightedText(item.excerpt, item.highlight_terms)}
                </blockquote>
                <div className="answer-evidence__links">
                  <a className="evidence-cta evidence-cta-primary" href={item.reader_url} target="_blank" rel="noreferrer">
                    <span>{item.link_label}</span>
                    <ExternalLink aria-hidden="true" size={15} />
                  </a>
                  {item.reader_url !== item.source_url && (
                    <a className="evidence-cta" href={item.source_url} target="_blank" rel="noreferrer">
                      <span>View source</span>
                      <ExternalLink aria-hidden="true" size={15} />
                    </a>
                  )}
                </div>
              </article>
            ))}
          </div>

          <aside className="answer-tip" aria-label="Evidence reading tip">
            <Lightbulb aria-hidden="true" size={17} />
            <p>
              Start with the first highlighted card. It is the primary proof, while the links keep the readable docs page
              separate from source provenance.
            </p>
          </aside>
        </>
      ) : (
        <p className="empty-state">Evidence excerpts will appear here after the answer endpoint returns grounded sources.</p>
      )}

      {links.length > 0 && (
        <div className="important-links">
          <h3>Important links</h3>
          <ul>
            {links.map((link) => (
              <li key={`${link.title}-${link.url}`}>
                <a href={link.url} target="_blank" rel="noreferrer">
                  <span>{link.title}</span>
                  <span className="important-links__label">{link.link_label ?? "Open"}</span>
                  <ExternalLink aria-hidden="true" size={14} />
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function importantLinks(answer: AnswerResponse | null): Source[] {
  if (!answer) {
    return [];
  }

  if (answer.links.length > 0) {
    return answer.links.slice(0, 3);
  }

  return answer.evidence.slice(0, 3).map((item) => ({
    title: item.title,
    url: item.reader_url,
    link_label: item.link_label
  }));
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
