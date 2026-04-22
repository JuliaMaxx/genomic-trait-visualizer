type Props = {
  label: string;
  value: string;
  tone?: 'default' | 'accent';
};

function StatPill({ label, value, tone = 'default' }: Props) {
  const toneClass =
    tone === 'accent'
      ? 'border-brand-line bg-brand-soft text-content'
      : 'border-border bg-surface-overlay text-content-muted';

  return (
    <div className={`rounded-pill border px-pill-x py-pill-y text-sm ${toneClass}`}>
      <span className="text-content-faint">{label}</span> {value}
    </div>
  );
}

export default StatPill;
