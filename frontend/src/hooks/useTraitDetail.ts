import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchTraitDetail } from '../services/traitApi';
import type { TraitDetail } from '../types/analysis';

function useTraitDetail(traitId: string | undefined) {
  const [traitDetail, setTraitDetail] = useState<TraitDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const controllerRef = useRef<AbortController | null>(null);

  const loadDetail = useCallback(async () => {
    controllerRef.current?.abort();

    if (!traitId) {
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
      const data = await fetchTraitDetail(traitId, controller.signal);

      if (!controller.signal.aborted) {
        setTraitDetail(data);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setTraitDetail(null);
        setErrorMessage(
          error instanceof Error
            ? error.message
            : 'Something went wrong while loading trait details.',
        );
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
        controllerRef.current = null;
      }
    }
  }, [traitId]);

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

export default useTraitDetail;
