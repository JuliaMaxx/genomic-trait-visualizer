import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import StatPill from '../components/StatPill';
import { fetchTraitCatalog } from '../services/traitApi';
import type { TraitDefinition } from '../types/analysis';
import {
  formatCategoryLabel,
  formatEvidenceLabel,
} from '../utils/formatResultLabel';

function TraitCatalogPage() {
  const [traits, setTraits] = useState<TraitDefinition[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isCancelled = false;

    async function loadCatalog() {
      setIsLoading(true);
      setErrorMessage('');

      try {
        const data = await fetchTraitCatalog();
        if (!isCancelled) {
          setTraits(data);
        }
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Something went wrong while loading the trait catalog.',
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    loadCatalog();

    return () => {
      isCancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-1 flex-col gap-grid-gap py-card-padding">
      <section className="ui-panel-gradient">
        <p className="ui-eyebrow">trait catalog</p>
        <h1 className="mt-section-offset-sm max-w-(--width-text) text-3xl sm:text-4xl">
          Explore every trait currently used by the system.
        </h1>
        <p className="mt-section-offset-md max-w-(--width-text) text-base leading-body text-content-subtle">
          This is the browsing catalog for every trait in the current model.
          Each page starts with a plain-English explanation, then opens into
          genetic contributors, research spotlight, sources, and cross-links to
          rsIDs.
        </p>
        <p className="mt-section-offset-lg text-xs leading-body text-content-faint">
          Educational, not medical advice. Effects are probabilistic and
          research can vary by study or population.
        </p>
      </section>

      {isLoading ? (
        <div className="ui-panel">Loading trait catalog.</div>
      ) : null}

      {errorMessage ? (
        <div className="ui-panel-error">{errorMessage}</div>
      ) : null}

      <div className="grid gap-panel-padding md:grid-cols-2">
        {traits.map((trait) => (
          <Link
            key={trait.id}
            to={`/traits/${trait.id}`}
            className="group ui-card-link"
          >
            <div>
              <p className="ui-eyebrow">
                {formatCategoryLabel(trait.category)}
              </p>
              <h2 className="ui-card-link-heading mt-section-offset-sm text-xl text-content">
                {trait.name}
              </h2>
              <p className="mt-section-offset-sm text-sm leading-body text-content-subtle">
                {trait.simple_summary}
              </p>
            </div>
            <div className="mt-section-offset-xl flex flex-wrap gap-inline-gap-sm">
              <StatPill
                label="Evidence"
                value={formatEvidenceLabel(trait.evidence_level)}
                tooltip="Evidence describes how strong the overall research support is for this simplified trait model."
              />
              <StatPill
                label="Keywords"
                value={String(trait.keywords.length)}
                tone="accent"
                tooltip="Keywords are alternate names or search terms for this trait in the catalog."
              />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default TraitCatalogPage;
