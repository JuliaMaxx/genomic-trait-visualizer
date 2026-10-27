import { Link, Navigate } from 'react-router-dom';
import { useState } from 'react';
import { useAnalysisSession } from '../context/useAnalysisSession';
import useTraitOverview from '../hooks/useTraitOverview';
import {
  filterAnalysisTraits,
  type AnalysisFilters,
} from '../utils/searchFilters';

import StatPill from '../components/StatPill';
import TraitCard from '../components/TraitCard';
import Button from '../components/Button';
import LinkButton from '../components/LinkButton';
import FilterPanel from '../components/FilterPanel';

function AnalysisPage() {
  const { selectedFile } = useAnalysisSession();
  const { traits, errorMessage, isLoading, retry } =
    useTraitOverview(selectedFile);

  const [filters, setFilters] = useState<AnalysisFilters>({
    query: '',
    likelihood: 'all',
    confidence: 'all',
    category: 'all',
  });

  if (!selectedFile) {
    return <Navigate to="/" replace />;
  }

  const likelihoods = [
    { value: 'all', label: 'All likelihoods' },
    { value: 'likely', label: 'Likely' },
    { value: 'unlikely', label: 'Unlikely' },
    { value: 'inconclusive', label: 'Inconclusive' },
  ];

  const confidenceLevels = [
    { value: 'all', label: 'All confidence' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  const categories = [
    { value: 'all', label: 'All categories' },
    { value: 'nutrition', label: 'Nutrition' },
    { value: 'appearance', label: 'Appearance' },
    { value: 'health', label: 'Health' },
    { value: 'behavior', label: 'Behavior' },
  ];

  const traitsWithObservedRsids = traits.filter(
    (trait) => trait.observed_rsids.length > 0,
  );
  const visibleTraits = filterAnalysisTraits(traits, filters);
  const matchedTraitCount = traitsWithObservedRsids.filter(
    (trait) => trait.matched_rsids.length > 0,
  ).length;
  const deterministicCount = traitsWithObservedRsids.filter(
    (trait) => trait.result === 'likely' || trait.result === 'unlikely',
  ).length;
  const averageCoverage =
    traitsWithObservedRsids.length > 0
      ? Math.round(
          (traitsWithObservedRsids.reduce(
            (sum, trait) => sum + trait.coverage,
            0,
          ) /
            traitsWithObservedRsids.length) *
            100,
        )
      : 0;

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
      <div className="ui-empty-state">
        Reading your uploaded DNA and evaluating mapped traits...
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="ui-panel-error flex justify-between items-center">
        <p>{errorMessage}</p>
        <Button onClick={() => void retry()}>Retry</Button>
      </div>
    );
  }

  if (traitsWithObservedRsids.length === 0) {
    return (
      <div>
        <div className="ui-empty-state flex justify-between items-center flex-wrap gap-sm">
          No traits with usable rsIDs were found for this upload.
          <LinkButton to="/" variant="secondary">
            Try a different file
          </LinkButton>
        </div>
      </div>
    );
  }

  return (
    <div className="ui-page-stack">
      <section className="ui-panel-gradient grid gap-xl grid-cols-1 lg:grid-cols-[auto_1fr]">
        <div>
          <p className="ui-eyebrow">Trait analysis</p>
          <h1 className="ui-detail-title mb-lg">Trait analysis results.</h1>
          <p className="ui-detail-lede">
            Here are shown all the traits that could be checked using your
            uploaded DNA file.Each card below gives a quick read on one trait.
            Open any trait to see which rsIDs were found, which genotypes
            matched the rule set, and how the final interpretation was produced.
          </p>
          <p className="ui-detail-note">
            Educational, not medical advice. SNP effects are probabilistic and
            research can vary by study or population.
          </p>
        </div>
        <div className="ui-panel-subtle p-xl">
          <div className="flex justify-start items-center gap-sm">
            <p className="ui-paragraph-strong">
              Results for{' '}
              <Link to="/" className="ui-link">
                {selectedFile.name}
              </Link>
            </p>
          </div>

          <div className="ui-pill-collection">
            <StatPill
              label="Shown traits"
              value={String(traitsWithObservedRsids.length)}
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
      </section>

      <FilterPanel
        searchValue={filters.query}
        onSearchChange={(query) =>
          setFilters((current) => ({
            ...current,
            query,
          }))
        }
        searchPlaceholder="Trait, keyword, rsID"
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filters={[
          {
            id: 'likelihood',
            label: 'Likelihood',
            ariaLabel: 'Likelihood filter',
            value: filters.likelihood,
            onChange: (likelihood) => {
              if (likelihoods.map((l) => l.value).includes(likelihood)) {
                setFilters((current) => ({
                  ...current,
                  likelihood: likelihood as typeof filters.likelihood,
                }));
              }
            },
            options: likelihoods,
          },
          {
            id: 'confidence',
            label: 'Confidence',
            ariaLabel: 'Confidence filter',
            value: filters.confidence,
            onChange: (confidence) => {
              if (confidenceLevels.map((c) => c.value).includes(confidence)) {
                setFilters((current) => ({
                  ...current,
                  confidence: confidence as typeof filters.confidence,
                }));
              }
            },
            options: confidenceLevels,
          },
          {
            id: 'category',
            label: 'Category',
            ariaLabel: 'Category filter',
            value: filters.category,
            onChange: (category) => {
              if (categories.map((c) => c.value).includes(category)) {
                setFilters((current) => ({
                  ...current,
                  category: category as typeof filters.category,
                }));
              }
            },
            options: categories,
          },
        ]}
      />

      {visibleTraits.length === 0 ? (
        <div className="ui-empty-state">
          No analysis traits match the current search and filters.
        </div>
      ) : null}

      <div className="grid gap-xl md:grid-cols-2">
        {visibleTraits.map((trait) => (
          <TraitCard key={trait.trait_id} trait={trait} />
        ))}
      </div>
    </div>
  );
}

export default AnalysisPage;
