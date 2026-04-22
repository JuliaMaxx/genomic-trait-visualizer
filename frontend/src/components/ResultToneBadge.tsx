import type { TraitResultLabel } from '../types/analysis';
import { formatResultLabel } from '../utils/formatResultLabel';

type Props = {
  result: TraitResultLabel;
};

const toneClasses: Record<TraitResultLabel, string> = {
  likely: 'border-emerald-400/25 bg-emerald-400/10 text-emerald-100',
  unlikely: 'border-rose-400/25 bg-rose-400/10 text-rose-100',
  inconclusive: 'border-amber-300/25 bg-amber-300/10 text-amber-100',
};

function ResultToneBadge({ result }: Props) {
  return (
    <span
      className={`rounded-pill border px-badge-x py-badge-y text-xs font-medium tracking-tight ${toneClasses[result]}`}
    >
      {formatResultLabel(result)}
    </span>
  );
}

export default ResultToneBadge;
