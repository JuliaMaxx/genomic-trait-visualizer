import { useEffect, useState } from 'react';

import StatPill from '../components/StatPill';
import FilterDropdown from '../components/FilterDropdown';
import TeaserCard from '../components/TeaserCard';
import { fetchTraitCatalog } from '../services/traitApi';
import type { TraitDefinition } from '../types/analysis';
import {
  formatCategoryLabel,
  formatEvidenceLabel,
} from '../utils/formatResultLabel';
import {
  filterTraitCatalog,
  type TraitCatalogFilters,
} from '../utils/searchFilters';

function TraitCatalogPage() {
  const [traits, setTraits] = useState<TraitDefinition[]>([]);
  const [filters, setFilters] = useState<TraitCatalogFilters>({
    query: '',
    category: 'all',
    evidence: 'all',
  });
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const visibleTraits = filterTraitCatalog(traits, filters);
  const hasActiveFilters =
    filters.query !== '' ||
    filters.category !== 'all' ||
    filters.evidence !== 'all';

  function resetFilters() {
    setFilters({
      query: '',
      category: 'all',
      evidence: 'all',
    });
  }

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
        <h1 className="ui-detail-title max-w-(--width-text)">
          Explore every trait currently used by the system.
        </h1>
        <p className="ui-detail-lede max-w-(--width-text)">
          This is the browsing catalog for every trait in the current model.
          Each page starts with a plain-English explanation, then opens into
          genetic contributors, research spotlight, sources, and cross-links to
          rsIDs.
        </p>
        <p className="ui-detail-note">
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

      <div className="ui-filter-panel">
        <div className="flex items-start justify-between gap-inline-gap-sm">
          <div className="ui-filter-grid flex-1">
            <label className="ui-filter-label">
              Search
              <input
                className="ui-search-input"
                value={filters.query}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    query: event.target.value,
                  }))
                }
                placeholder="Trait, keyword, gene, rsID"
                type="search"
              />
            </label>
            <label className="ui-filter-label">
              Category
              <FilterDropdown
                ariaLabel="Category filter"
                value={filters.category}
                onChange={(category) =>
                  setFilters((current) => ({
                    ...current,
                    category,
                  }))
                }
                options={[
                  { value: 'all', label: 'All categories' },
                  { value: 'nutrition', label: 'Nutrition' },
                  { value: 'appearance', label: 'Appearance' },
                  { value: 'health', label: 'Health' },
                  { value: 'behavior', label: 'Behavior' },
                ]}
              />
            </label>
            <label className="ui-filter-label">
              Evidence
              <FilterDropdown
                ariaLabel="Evidence filter"
                value={filters.evidence}
                onChange={(evidence) =>
                  setFilters((current) => ({
                    ...current,
                    evidence,
                  }))
                }
                options={[
                  { value: 'all', label: 'All evidence' },
                  { value: 'strong', label: 'Strong' },
                  { value: 'moderate', label: 'Moderate' },
                  { value: 'limited', label: 'Limited' },
                ]}
              />
            </label>
          </div>
          {hasActiveFilters ? (
            <button
              type="button"
              className="ui-filter-reset-button"
              aria-label="Reset filters"
              title="Reset filters"
              onClick={resetFilters}
            />
          ) : null}
        </div>
      </div>

      {!isLoading && visibleTraits.length === 0 ? (
        <div className="ui-empty-state">
          No catalog traits match the current search and filters.
        </div>
      ) : null}

      <div className="grid gap-panel-padding md:grid-cols-2">
        {visibleTraits.map((trait) => (
          <TeaserCard
            key={trait.id}
            to={`/traits/${trait.id}`}
            eyebrow={formatCategoryLabel(trait.category)}
            title={trait.name}
            description={trait.simple_summary}
            footer={
              <>
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
              </>
            }
          />
        ))}
      </div>
    </div>
  );
}

export default TraitCatalogPage;
