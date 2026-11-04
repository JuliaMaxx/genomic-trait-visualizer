import type { TraitSource } from '../types/api';

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
      <p className="ui-item-body">{source.reference}</p>
      <p className="ui-detail-note">{source.notes}</p>
    </a>
  );
}

export default SourceLink;
