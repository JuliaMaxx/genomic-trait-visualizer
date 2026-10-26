import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchRsidCatalog } from '../services/traitApi';
import type { RsidCatalogItem } from '../types/analysis';

function useRsidCatalog() {
  const [rsids, setRsids] = useState<RsidCatalogItem[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const controllerRef = useRef<AbortController | null>(null);

  const loadCatalog = useCallback(async () => {
    controllerRef.current?.abort();

    const controller = new AbortController();
    controllerRef.current = controller;

    setIsLoading(true);
    setErrorMessage('');

    try {
      const data = await fetchRsidCatalog(controller.signal);

      if (!controller.signal.aborted) {
        setRsids(data);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        console.error('Failed to load rsID catalog:', error);
        setErrorMessage('Unable to load the rsID catalog. Please try again.');
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadCatalog();

    return () => {
      controllerRef.current?.abort();
    };
  }, [loadCatalog]);

  return {
    rsids,
    errorMessage,
    isLoading,
    retry: loadCatalog,
  };
}

export default useRsidCatalog;
