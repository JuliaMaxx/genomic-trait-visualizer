import { createContext } from 'react';

export type AnalysisSession = {
  selectedFile: File | null;
  setSelectedFile: (file: File | null) => void;
};

export const AnalysisSessionContext = createContext<
  AnalysisSession | undefined
>(undefined);
