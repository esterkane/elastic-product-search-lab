import type { DisplayMetadata } from "../lib/resultFormatter";

type SourceMetadataProps = {
  display: DisplayMetadata;
  compact?: boolean;
  includeTitle?: boolean;
};

export function SourceMetadata({ display, compact = false, includeTitle = false }: SourceMetadataProps) {
  return (
    <dl className={`metadata-list ${compact ? "metadata-list-compact" : "metadata-list-inline"}`}>
      {includeTitle && (
        <div>
          <dt>Source</dt>
          <dd>{display.displayTitle}</dd>
        </div>
      )}
      {display.displaySection && (
        <div>
          <dt>Section</dt>
          <dd>{display.displaySection}</dd>
        </div>
      )}
      {display.displayFile && (
        <div>
          <dt>File</dt>
          <dd>{display.displayFile}</dd>
        </div>
      )}
      {display.displayRepo && (
        <div>
          <dt>Repo</dt>
          <dd>{display.displayRepo}</dd>
        </div>
      )}
    </dl>
  );
}
