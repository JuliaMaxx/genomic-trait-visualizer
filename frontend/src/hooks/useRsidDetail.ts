import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchRsidDetail } from '../services/traitApi';
import type { RsidDetail } from '../types/analysis';

function useRsidDetail(rsid: string | undefined) {
  const [detail, setDetail] = useState<RsidDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const controllerRef = useRef<AbortController | null>(null);

  const loadDetail = useCallback(async () => {
    controllerRef.current?.abort();

    if (!rsid) {
      controllerRef.current = null;
      setDetail(null);
      setErrorMessage('');
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;

    setIsLoading(true);
    setErrorMessage('');

    try {
      const data = await fetchRsidDetail(rsid, controller.signal);

      if (!controller.signal.aborted) {
        setDetail(data);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setDetail(null);
        setErrorMessage(
          error instanceof Error
            ? error.message
            : 'Something went wrong while loading this rsID.',
        );
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
        controllerRef.current = null;
      }
    }
  }, [rsid]);

  useEffect(() => {
    void loadDetail();

    return () => {
      controllerRef.current?.abort();
    };
  }, [loadDetail]);

  return {
    detail,
    errorMessage,
    isLoading,
    retry: loadDetail,
  };
}

export default useRsidDetail;
