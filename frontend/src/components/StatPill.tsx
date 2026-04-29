import InfoTooltip from './InfoTooltip';

type Props = {
  label: string;
  value: string;
  tone?: 'default' | 'accent';
  tooltip?: string;
};

function StatPill({ label, value, tone = 'default', tooltip }: Props) {
  const toneClass =
    tone === 'accent' ? 'ui-stat-pill-accent' : 'ui-stat-pill-default';

  return (
    <div className={`ui-stat-pill ${toneClass}`}>
      <span className="ui-stat-pill-label">
        <span>{label}</span>
        {tooltip ? <InfoTooltip content={tooltip} /> : null}
      </span>
      <span>{value}</span>
    </div>
  );
}

export default StatPill;
