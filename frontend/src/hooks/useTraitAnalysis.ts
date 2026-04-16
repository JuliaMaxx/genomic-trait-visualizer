import { useEffect, useState } from 'react';
import { analyzeDnaFile } from '../services/analyzeDnaFile';

function useTraitAnalysis(file: File | null) {
  const [traits, setTraits] = useState<Trait[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!file) {
      setTraits([]);
      setErrorMessage('');
      setIsLoading(false);
      return;
    }

    let isCancelled = false; // TODO: use AbortController instead of this flag

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
              : 'Something went wrong while contacting the backend.',
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false); // TODO: avoid retetting loading manually
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

export default useTraitAnalysis;
