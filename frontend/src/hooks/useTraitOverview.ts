import { useCallback, useEffect, useRef, useState } from 'react';
import { analyzeDnaFile } from '../services/traitApi';
import type { TraitResult } from '../types/analysis';

function useTraitOverview(file: File | null) {
  const [traits, setTraits] = useState<TraitResult[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const controllerRef = useRef<AbortController | null>(null);

  const loadTraits = useCallback(async () => {
    controllerRef.current?.abort();

    if (!file) {
      controllerRef.current = null;
      setTraits([]);
      setErrorMessage('');
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;

    setIsLoading(true);
    setErrorMessage('');

    try {
      const data = await analyzeDnaFile(file, controller.signal);

      if (!controller.signal.aborted) {
        setTraits(data);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        console.error('Failed to analyze DNA file:', error);
        setTraits([]);
        setErrorMessage('Unable to analyze your DNA file. Please try again.');
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
        controllerRef.current = null;
      }
    }
  }, [file]);

  useEffect(() => {
    void loadTraits();

    return () => {
      controllerRef.current?.abort();
    };
  }, [loadTraits]);

  return {
    traits,
    errorMessage,
    isLoading,
    retry: loadTraits,
  };
}

export default useTraitOverview;
