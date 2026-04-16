import { useContext } from 'react';
import { AnalysisSessionContext } from './AnalysisSessionContext';

export function useAnalysisSession() {
  const ctx = useContext(AnalysisSessionContext);
  if (!ctx) throw new Error('useAnalysisSession must be used inside provider');
  return ctx;
}
