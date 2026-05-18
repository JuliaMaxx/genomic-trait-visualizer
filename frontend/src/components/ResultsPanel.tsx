import { useState } from 'react';
import type { TraitResult } from '../types/analysis';
import {
  filterAnalysisTraits,
  type AnalysisFilters,
} from '../utils/searchFilters';
import FilterDropdown from './FilterDropdown';
import StatPill from './StatPill';
import TraitCard from './TraitCard';

type Props = {
  errorMessage: string;
  isLoading: boolean;
  selectedFile: File;
  traits: TraitResult[];
};

function ResultsPanel({
  errorMessage,
  isLoading,
  selectedFile,
  traits,
}: Props) {
  const [filters, setFilters] = useState<AnalysisFilters>({
    query: '',
    likelihood: 'all',
    confidence: 'all',
    category: 'all',
  });
  const traitsWithObservedRsids = traits.filter(
    (trait) => trait.observed_rsids.length > 0,
  );
  const visibleTraits = filterAnalysisTraits(traits, filters);
  const hasActiveFilters =
    filters.query !== '' ||
    filters.likelihood !== 'all' ||
    filters.confidence !== 'all' ||
    filters.category !== 'all';

  function resetFilters() {
    setFilters({
      query: '',
      likelihood: 'all',
      confidence: 'all',
      category: 'all',
    });
  }

  if (isLoading) {
    return (
      <div className="ui-panel w-full max-w-(--width-content)">
        <p className="ui-eyebrow">analysis status</p>
        <p className="mt-section-offset-md text-base text-content">
          Reading your uploaded DNA and evaluating mapped traits.
        </p>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="ui-panel-error w-full max-w-(--width-content)">
        {errorMessage}
      </div>
    );
  }

  if (traitsWithObservedRsids.length === 0) {
    return (
      <div className="ui-panel w-full max-w-(--width-content) text-sm text-content-muted">
        No traits with usable rsIDs were found for this upload.
      </div>
    );
  }

  const matchedTraitCount = visibleTraits.filter(
    (trait) => trait.matched_rsids.length > 0,
  ).length;
  const deterministicCount = visibleTraits.filter(
    (trait) => trait.result === 'likely' || trait.result === 'unlikely',
  ).length;
  const averageCoverage =
    visibleTraits.length > 0
      ? Math.round(
          (visibleTraits.reduce((sum, trait) => sum + trait.coverage, 0) /
            visibleTraits.length) *
            100,
        )
      : 0;

  return (
    <div className="mx-auto flex w-full max-w-(--width-content) flex-col gap-stack-gap">
      <div className="ui-panel">
        <p className="ui-eyebrow">analysis summary</p>
        <p className="mt-section-offset-md text-lg font-medium leading-tight tracking-tight text-content">
          Results for <span className="text-brand">{selectedFile.name}</span>
        </p>
        <p className="mt-section-offset-sm max-w-(--width-text) text-sm leading-body text-content-subtle">
          Each card below gives a quick read on one trait. Open any trait to see
          which rsIDs were found, which genotypes matched the rule set, and how
          the final interpretation was produced.
        </p>

        <div className="mt-section-offset-xl flex flex-wrap gap-inline-gap-sm">
          <StatPill
            label="Shown traits"
            value={String(visibleTraits.length)}
            tooltip="Only traits with at least one rsID found in your uploaded file are shown here."
          />
          <StatPill
            label="Traits with matches"
            value={String(matchedTraitCount)}
            tone="accent"
            tooltip="These are traits where at least one of your observed genotypes matched a curated rule used by the model."
          />
          <StatPill
            label="Deterministic results"
            value={String(deterministicCount)}
            tooltip="Deterministic means the result leaned clearly one way or the other: either 'likely' or 'unlikely'. Inconclusive traits are not counted here."
          />
          <StatPill
            label="Average coverage"
            value={`${averageCoverage}%`}
            tooltip="Coverage tells you how much of each trait's rsID rule set could actually be checked using your uploaded DNA file."
          />
        </div>
      </div>

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
                placeholder="Trait, keyword, rsID"
                type="search"
              />
            </label>
            <label className="ui-filter-label">
              Likelihood
              <FilterDropdown
                ariaLabel="Likelihood filter"
                value={filters.likelihood}
                onChange={(likelihood) =>
                  setFilters((current) => ({
                    ...current,
                    likelihood,
                  }))
                }
                options={[
                  { value: 'all', label: 'All likelihoods' },
                  { value: 'likely', label: 'Likely' },
                  { value: 'unlikely', label: 'Unlikely' },
                  { value: 'inconclusive', label: 'Inconclusive' },
                ]}
              />
            </label>
            <label className="ui-filter-label">
              Confidence
              <FilterDropdown
                ariaLabel="Confidence filter"
                value={filters.confidence}
                onChange={(confidence) =>
                  setFilters((current) => ({
                    ...current,
                    confidence,
                  }))
                }
                options={[
                  { value: 'all', label: 'All confidence' },
                  { value: 'high', label: 'High' },
                  { value: 'medium', label: 'Medium' },
                  { value: 'low', label: 'Low' },
                ]}
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

      {visibleTraits.length === 0 ? (
        <div className="ui-empty-state">
          No analysis traits match the current search and filters.
        </div>
      ) : null}

      <div className="grid gap-panel-padding md:grid-cols-2">
        {visibleTraits.map((trait) => (
          <TraitCard key={trait.trait_id} trait={trait} />
        ))}
      </div>
    </div>
  );
}

export default ResultsPanel;
