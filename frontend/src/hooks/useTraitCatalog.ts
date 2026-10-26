import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchTraitCatalog } from '../services/traitApi';
import type { TraitDefinition } from '../types/analysis';

function useTraitCatalog() {
  const [traits, setTraits] = useState<TraitDefinition[]>([]);
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
      const data = await fetchTraitCatalog(controller.signal);

      if (!controller.signal.aborted) {
        setTraits(data);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        console.error('Failed to load trait catalog:', error);
        setErrorMessage('Unable to load the trait catalog. Please try again.');
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
    traits,
    errorMessage,
    isLoading,
    retry: loadCatalog,
  };
}

export default useTraitCatalog;
