import type { TraitSource } from '../types/analysis';

type SourceLinkProps = {
  source: TraitSource;
};

function SourceLink({ source }: SourceLinkProps) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="ui-panel-subtle ui-interactive-border-accent"
    >
      <p className="ui-item-title">{source.name}</p>

      {source.reference ? (
        <p className="ui-item-body">{source.reference}</p>
      ) : null}

      {source.notes ? <p className="ui-detail-note">{source.notes}</p> : null}
    </a>
  );
}

export default SourceLink;
