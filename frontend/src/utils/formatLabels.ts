import type { EvidenceLevel, TraitResultLabel } from '../types/analysis';

export function formatResultLabel(result: TraitResultLabel) {
  return result.charAt(0).toUpperCase() + result.slice(1);
}

export function formatEvidenceLabel(level: EvidenceLevel) {
  return level.charAt(0).toUpperCase() + level.slice(1);
}
