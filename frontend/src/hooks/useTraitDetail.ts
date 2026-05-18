import { useEffect, useState } from 'react';
import { evaluateTrait, fetchTraitDetail } from '../services/traitApi';
import type { TraitDetail } from '../types/analysis';

function useTraitDetail(file: File | null, traitId: string) {
  const [traitDetail, setTraitDetail] = useState<TraitDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!traitId) {
      setTraitDetail(null);
      setErrorMessage('');
      setIsLoading(false);
      return;
    }

    let isCancelled = false;

    async function loadTraitDetail() {
      setIsLoading(true);
      setErrorMessage('');

      try {
        const data = file
          ? await evaluateTrait(traitId, file)
          : await fetchTraitDetail(traitId);

        if (!isCancelled) {
          setTraitDetail(data);
        }
      } catch (error) {
        if (!isCancelled) {
          setTraitDetail(null);
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Something went wrong while loading trait details.',
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    loadTraitDetail();

    return () => {
      isCancelled = true;
    };
  }, [file, traitId]);

  return {
    traitDetail,
    errorMessage,
    isLoading,
  };
}

export default useTraitDetail;
