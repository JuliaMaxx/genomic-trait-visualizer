import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import StatPill from '../components/StatPill';
import FilterDropdown from '../components/FilterDropdown';
import { fetchRsidCatalog } from '../services/traitApi';
import type { RsidCatalogItem } from '../types/analysis';
import { formatEvidenceLabel } from '../utils/formatResultLabel';
import {
  filterRsidCatalog,
  type RsidCatalogFilters,
} from '../utils/searchFilters';

function RsidCatalogPage() {
  const [rsids, setRsids] = useState<RsidCatalogItem[]>([]);
  const [filters, setFilters] = useState<RsidCatalogFilters>({
    query: '',
    evidence: 'all',
  });
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const visibleRsids = filterRsidCatalog(rsids, filters);
  const hasActiveFilters = filters.query !== '' || filters.evidence !== 'all';

  function resetFilters() {
    setFilters({
      query: '',
      evidence: 'all',
    });
  }

  useEffect(() => {
    let isCancelled = false;

    async function loadCatalog() {
      setIsLoading(true);
      setErrorMessage('');

      try {
        const data = await fetchRsidCatalog();
        if (!isCancelled) {
          setRsids(data);
        }
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Something went wrong while loading the rsID catalog.',
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
        <p className="ui-eyebrow">rsID catalog</p>
        <h1 className="mt-section-offset-sm max-w-(--width-text) text-3xl sm:text-4xl">
          Browse the SNP markers behind the trait system.
        </h1>
        <p className="mt-section-offset-md max-w-(--width-text) text-base leading-body text-content-subtle">
          Each marker page starts with the technical rule data, then lets you
          expand the plain-English story, linked traits, and sources.
        </p>
        <p className="mt-section-offset-lg text-xs leading-body text-content-faint">
          Educational, not medical advice. SNP effects are probabilistic and
          research can vary by study or population.
        </p>
      </section>

      {isLoading ? <div className="ui-panel">Loading rsID catalog.</div> : null}

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
              placeholder="rsID, gene, trait keyword"
              type="search"
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

      {!isLoading && visibleRsids.length === 0 ? (
        <div className="ui-empty-state">
          No rsIDs match the current search and filters.
        </div>
      ) : null}

      <div className="grid gap-panel-padding md:grid-cols-2 lg:grid-cols-3">
        {visibleRsids.map((rsid) => (
          <Link
            key={rsid.rsid}
            to={`/rsids/${rsid.rsid}`}
            className="group ui-card-link"
          >
            <div>
              <p className="ui-eyebrow">{rsid.gene ?? 'genetic marker'}</p>
              <h2 className="ui-card-link-heading mt-section-offset-sm font-mono text-xl text-content">
                {rsid.rsid}
              </h2>
              <p className="mt-section-offset-sm text-sm leading-body text-content-subtle">
                {rsid.plain_english_summary}
              </p>
            </div>
            <div className="mt-section-offset-xl flex flex-wrap gap-inline-gap-sm">
              <StatPill
                label="Linked traits"
                value={String(rsid.trait_count)}
                tone="accent"
                tooltip="How many current trait models use this marker."
              />
              {rsid.evidence_level ? (
                <StatPill
                  label="Evidence"
                  value={formatEvidenceLabel(rsid.evidence_level)}
                  tooltip="Strongest evidence level among current rules using this rsID."
                />
              ) : null}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default RsidCatalogPage;
