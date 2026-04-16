import { useState } from 'react';
import { WithChildren } from '../types/react';
import { AnalysisSessionContext } from './AnalysisSessionContext';

export function AnalysisSessionProvider({ children }: WithChildren) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  return (
    <AnalysisSessionContext.Provider value={{ selectedFile, setSelectedFile }}>
      {children}
    </AnalysisSessionContext.Provider>
  );
}
