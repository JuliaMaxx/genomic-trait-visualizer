import type { TraitResultLabel } from '../types/analysis';
import { formatResultLabel } from '../utils/formatResultLabel';
import InfoTooltip from './InfoTooltip';

type Props = {
  result: TraitResultLabel;
  tooltip?: string;
};

const toneClasses: Record<TraitResultLabel, string> = {
  likely: 'ui-result-tone-likely',
  unlikely: 'ui-result-tone-unlikely',
  inconclusive: 'ui-result-tone-inconclusive',
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
