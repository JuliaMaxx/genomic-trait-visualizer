import type { TraitResultLabel } from '../types/analysis';
import { formatResultLabel } from '../utils/formatLabels';
import InfoTooltip from './InfoTooltip';

type Props = {
  result: TraitResultLabel;
  tooltip?: string;
};

const toneClasses: Record<TraitResultLabel, string> = {
  likely: 'ui-badge-success',
  unlikely: 'ui-badge-danger',
  inconclusive: 'ui-badge-warning',
};

function ResultToneBadge({ result, tooltip }: Props) {
  return (
    <span className={`ui-result-badge ${toneClasses[result]}`}>
      {formatResultLabel(result)}
      {tooltip ? <InfoTooltip content={tooltip} /> : null}
    </span>
  );
}

export default ResultToneBadge;
