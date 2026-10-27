import { useState } from 'react';

import StatPill from '../components/StatPill';
import TeaserCard from '../components/TeaserCard';
import { formatEvidenceLabel } from '../utils/formatLabels';
import {
  filterRsidCatalog,
  type RsidCatalogFilters,
} from '../utils/searchFilters';
import Button from '../components/Button';
import useRsidCatalog from '../hooks/useRsidCatalog';
import FilterPanel from '../components/FilterPanel';

function RsidCatalogPage() {
  const { rsids, errorMessage, isLoading, retry } = useRsidCatalog();
  const [filters, setFilters] = useState<RsidCatalogFilters>({
    query: '',
    evidence: 'all',
  });
  const visibleRsids = filterRsidCatalog(rsids, filters);

  const hasActiveFilters = filters.query !== '' || filters.evidence !== 'all';

  const evidenceLevels = [
    { value: 'all', label: 'All evidence' },
    { value: 'strong', label: 'Strong' },
    { value: 'moderate', label: 'Moderate' },
    { value: 'limited', label: 'Limited' },
  ];

  function resetFilters() {
    setFilters({
      query: '',
      evidence: 'all',
    });
  }

  if (isLoading) {
    return <div className="ui-empty-state">Loading rsID catalog...</div>;
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
        <p className="ui-eyebrow">rsID catalog</p>
        <h1 className="ui-detail-title mb-lg">
          Browse the SNP markers behind the trait system.
        </h1>
        <p className="ui-detail-lede">
          This is a browsing catalog for every rsID in the current model. See
          plain-English explainations, technical rule data, research behind it,
          linked traits, and sources.
        </p>
        <p className="ui-detail-note">
          Educational, not medical advice. SNP effects are probabilistic and
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
        searchPlaceholder="rsID, gene, trait keyword"
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filters={[
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

      {visibleRsids.length === 0 ? (
        <div className="ui-empty-state" role="status" aria-live="polite">
          No rsIDs match the current search and filters.
        </div>
      ) : null}

      <div className="grid gap-3xl md:grid-cols-2 lg:grid-cols-3">
        {visibleRsids.map((rsid) => (
          <TeaserCard
            key={rsid.rsid}
            to={`/rsids/${rsid.rsid}`}
            eyebrow={rsid.gene ?? 'genetic marker'}
            title={rsid.rsid}
            description={rsid.plain_english_summary}
            size="lg"
            footer={
              <>
                {rsid.evidence_level ? (
                  <StatPill
                    label="Evidence"
                    value={formatEvidenceLabel(rsid.evidence_level)}
                    tone="accent"
                    tooltip="Strongest evidence level among current rules using this rsID."
                  />
                ) : null}
                <StatPill
                  label="Linked traits"
                  value={String(rsid.trait_count)}
                  tooltip="How many current trait models use this marker."
                />
              </>
            }
          />
        ))}
      </div>
    </div>
  );
}

export default RsidCatalogPage;
