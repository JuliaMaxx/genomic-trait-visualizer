import { useCallback, useEffect, useRef, useState } from 'react';
import { evaluateTrait } from '../services/traitApi';
import type { TraitDetail } from '../types/analysis';

function useTraitDetailAnalysis(
  file: File | null,
  traitId: string | undefined,
) {
  const [traitDetail, setTraitDetail] = useState<TraitDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const controllerRef = useRef<AbortController | null>(null);

  const loadDetail = useCallback(async () => {
    controllerRef.current?.abort();

    if (!file || !traitId) {
      controllerRef.current = null;
      setTraitDetail(null);
      setErrorMessage('');
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;

    setIsLoading(true);
    setErrorMessage('');

    try {
      const data = await evaluateTrait(traitId, file, controller.signal);

      if (!controller.signal.aborted) {
        setTraitDetail(data);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setTraitDetail(null);
        setErrorMessage(
          error instanceof Error
            ? error.message
            : 'Something went wrong while analyzing this trait.',
        );
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
        controllerRef.current = null;
      }
    }
  }, [file, traitId]);

  useEffect(() => {
    void loadDetail();

    return () => {
      controllerRef.current?.abort();
    };
  }, [loadDetail]);

  return {
    traitDetail,
    errorMessage,
    isLoading,
    retry: loadDetail,
  };
}

export default useTraitDetailAnalysis;
