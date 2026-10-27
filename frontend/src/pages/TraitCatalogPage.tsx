import { useState } from 'react';
import StatPill from '../components/StatPill';
import TeaserCard from '../components/TeaserCard';
import { formatEvidenceLabel } from '../utils/formatLabels';
import {
  filterTraitCatalog,
  type TraitCatalogFilters,
} from '../utils/searchFilters';
import Button from '../components/Button';
import useTraitCatalog from '../hooks/useTraitCatalog';
import FilterPanel from '../components/FilterPanel';

function TraitCatalogPage() {
  const { traits, errorMessage, isLoading, retry } = useTraitCatalog();
  const [filters, setFilters] = useState<TraitCatalogFilters>({
    query: '',
    category: 'all',
    evidence: 'all',
  });
  const visibleTraits = filterTraitCatalog(traits, filters);

  const hasActiveFilters =
    filters.query !== '' ||
    filters.category !== 'all' ||
    filters.evidence !== 'all';

  const categories = [
    { value: 'all', label: 'All categories' },
    { value: 'nutrition', label: 'Nutrition' },
    { value: 'appearance', label: 'Appearance' },
    { value: 'health', label: 'Health' },
    { value: 'behavior', label: 'Behavior' },
  ];

  const evidenceLevels = [
    { value: 'all', label: 'All evidence' },
    { value: 'strong', label: 'Strong' },
    { value: 'moderate', label: 'Moderate' },
    { value: 'limited', label: 'Limited' },
  ];

  function resetFilters() {
    setFilters({
      query: '',
      category: 'all',
      evidence: 'all',
    });
  }

  if (isLoading) {
    return <div className="ui-empty-state">Loading trait catalog...</div>;
  }

  if (errorMessage) {
    return (
      <div className="ui-panel-error flex justify-between items-center">
        <p>{errorMessage}</p>
        <Button onClick={() => void retry()}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="ui-page-stack">
      <section className="ui-panel-gradient">
        <p className="ui-eyebrow">trait catalog</p>
        <h1 className="ui-detail-title mb-lg">
          Explore every trait currently used by the system.
        </h1>
        <p className="ui-detail-lede">
          This is the browsing catalog for every trait in the current model. See
          plain-English explanations, genetic contributors, research spotlight,
          sources, and cross-links to rsIDs.
        </p>
        <p className="ui-detail-note">
          Educational, not medical advice. Effects are probabilistic and
          research can vary by study or population.
        </p>
      </section>

      <FilterPanel
        searchValue={filters.query}
        onSearchChange={(query) =>
          setFilters((current) => ({
            ...current,
            query,
          }))
        }
        searchPlaceholder="Trait, keyword, gene, rsID"
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filters={[
          {
            id: 'category',
            label: 'Category',
            ariaLabel: 'Category filter',
            value: filters.category,
            onChange: (value) => {
              if (categories.map((c) => c.value).includes(value)) {
                setFilters((current) => ({
                  ...current,
                  category: value as typeof filters.category,
                }));
              }
            },
            options: categories,
          },
          {
            id: 'evidence',
            label: 'Evidence',
            ariaLabel: 'Evidence filter',
            value: filters.evidence,
            onChange: (value) => {
              if (evidenceLevels.map((e) => e.value).includes(value)) {
                setFilters((current) => ({
                  ...current,
                  evidence: value as typeof filters.evidence,
                }));
              }
            },
            options: evidenceLevels,
          },
        ]}
      />

      {visibleTraits.length === 0 ? (
        <div className="ui-empty-state" role="status" aria-live="polite">
          No catalog traits match the current search and filters.
        </div>
      ) : null}

      <div className="grid gap-3xl md:grid-cols-2">
        {visibleTraits.map((trait) => (
          <TeaserCard
            key={trait.id}
            to={`/traits/${trait.id}`}
            eyebrow={trait.category}
            title={trait.name}
            description={trait.simple_summary}
            footer={
              <>
                <StatPill
                  label="Evidence"
                  value={formatEvidenceLabel(trait.evidence_level)}
                  tone="accent"
                  tooltip="Evidence describes how strong the overall research support is for this trait model."
                />
                <StatPill
                  label="Keywords"
                  value={String(trait.keywords.length)}
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
