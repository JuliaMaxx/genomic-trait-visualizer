import { createContext } from 'react';
import type { AnalysisSession } from '../types/session';

export const AnalysisSessionContext = createContext<
  AnalysisSession | undefined
>(undefined);
