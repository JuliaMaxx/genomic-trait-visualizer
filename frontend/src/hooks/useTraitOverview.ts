import { useEffect, useState } from 'react';
import { analyzeDnaFile } from '../services/traitApi';
import type { TraitResult } from '../types/analysis';

function useTraitOverview(file: File | null) {
  const [traits, setTraits] = useState<TraitResult[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!file) {
      setTraits([]);
      setErrorMessage('');
      setIsLoading(false);
      return;
    }

    let isCancelled = false;

    async function loadTraits() {
      setIsLoading(true);
      setErrorMessage('');

      try {
        const data = await analyzeDnaFile(file);

        if (!isCancelled) {
          setTraits(data);
        }
      } catch (error) {
        if (!isCancelled) {
          setTraits([]);
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Something went wrong while loading trait results.',
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    loadTraits();

    return () => {
      isCancelled = true;
    };
  }, [file]);

  return {
    traits,
    errorMessage,
    isLoading,
  };
}

export default useTraitOverview;
