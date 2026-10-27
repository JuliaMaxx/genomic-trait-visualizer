import { useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';

import Button from '../components/Button';
import StatPill from '../components/StatPill';
import TeaserCard from '../components/TeaserCard';
import useTraitDetail from '../hooks/useTraitDetail';
import { formatEvidenceLabel } from '../utils/formatLabels';
import DisclosurePanel from '../components/DisclosurePanel';
import SourceLink from '../components/SourceLink';

function TraitDetailPage() {
  const { traitId = '' } = useParams();
  const navigate = useNavigate();
  const [explanationMode, setExplanationMode] = useState<
    'simple' | 'technical'
  >('simple');
  const { traitDetail, errorMessage, isLoading } = useTraitDetail(traitId);
  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }

    navigate('/traits');
  };

  if (!traitId) {
    return <Navigate to="/traits" replace />;
  }

  if (isLoading) {
    return <div className="ui-empty-state">Loading trait detail...</div>;
  }

  if (errorMessage) {
    return (
      <div className="ui-panel-error flex justify-between items-center">
        <p>{errorMessage}</p>
        <Button onClick={handleBack}>Go back</Button>
      </div>
    );
  }

  if (traitDetail === null || Object.keys(traitDetail).length === 0) {
    return (
      <div className="ui-empty-state flex justify-between items-center">
        <p>No detail available for this trait.</p>
        <Button onClick={handleBack}>Go back</Button>
      </div>
    );
  }

  return (
    <div className="ui-page-stack">
      <div className="ui-page-toolbar">
        <Button type="button" variant="secondary" onClick={handleBack}>
          Go back
        </Button>
      </div>

      <section className="ui-panel-gradient">
        <div className="ui-detail-hero-layout">
          <div>
            <p className="ui-eyebrow">{traitDetail.category}</p>
            <h1 className="ui-detail-title">{traitDetail.name}</h1>
            <p className="ui-detail-lede-lg">{traitDetail.description}</p>
            <p className="ui-detail-note">
              Educational catalog entry. Not medical advice; effects are
              probabilistic and may vary across studies or populations.
            </p>
          </div>
          <div>
            {traitDetail.keywords.length > 0 ? (
              <div className="mt-lg">
                <p className="ui-eyebrow">keywords</p>
                <div className="mt-2xs flex flex-wrap gap-2xs">
                  {traitDetail.keywords.map((keyword, index) => (
                    <span key={`${keyword}-${index}`} className="ui-pill">
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
        <div className="ui-pill-collection">
          <StatPill
            label="Evidence"
            value={formatEvidenceLabel(traitDetail.evidence_level)}
            tooltip="Evidence describes the overall support behind this simplified model."
            tone="accent"
          />
          <StatPill
            label="rsIDs"
            value={String(traitDetail.rsids.length)}
            tooltip="Number of curated marker rules used by this trait."
          />
          <StatPill
            label="Sources"
            value={String(traitDetail.sources.length)}
            tooltip="Number of source cards attached to this trait."
          />
        </div>
      </section>

      <section className="mt-lg grid gap-md lg:grid-cols-2">
        <div className="ui-panel">
          <div className="flex items-center justify-between gap-md">
            <div>
              <p className="ui-eyebrow">trait field guide</p>
              <h2 className="ui-section-title">Different perspectives</h2>
            </div>
            <div className="ui-segmented-control">
              <button
                type="button"
                onClick={() => setExplanationMode('simple')}
                className={`ui-segmented-control-option ${
                  explanationMode === 'simple'
                    ? 'ui-segmented-control-option-active'
                    : 'ui-segmented-control-option-inactive'
                }`}
              >
                Simple
              </button>
              <button
                type="button"
                onClick={() => setExplanationMode('technical')}
                className={`ui-segmented-control-option ${
                  explanationMode === 'technical'
                    ? 'ui-segmented-control-option-active'
                    : 'ui-segmented-control-option-inactive'
                }`}
              >
                Technical
              </button>
            </div>
          </div>

          <div className="mt-lg ui-panel-accent">
            <p className="ui-eyebrow-accent">
              {explanationMode === 'simple'
                ? 'friendly view'
                : 'technical view'}
            </p>
            <div className="mt-lg grid gap-md">
              {(explanationMode === 'simple'
                ? traitDetail.simple_explanation
                : traitDetail.technical_explanation
              ).map((entry) => (
                <div key={entry.title} className="ui-panel-subtle">
                  <p className="ui-item-title">{entry.title}</p>
                  <p className="ui-item-body">{entry.body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="ui-panel">
          <p className="ui-eyebrow">everyday context</p>
          <h2 className="ui-section-title">Useful ways to think about it</h2>
          <div className="mt-lg grid gap-md">
            {traitDetail.practical_takeaway.map((entry) => (
              <div key={entry.title} className="ui-panel-subtle">
                <p className="ui-item-title">{entry.title}</p>
                <p className="ui-item-body">{entry.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="ui-panel-gradient border-brand-line">
        <div>
          <p className="ui-eyebrow">research spotlight</p>
          <h2 className="ui-section-title">Find out more about this trait</h2>
        </div>
        <div className="ui-section-content-grid">
          {traitDetail.research_spotlight.map((entry, index) => (
            <article
              key={entry.title}
              className={index < 2 ? 'ui-panel-accent' : 'ui-panel-subtle'}
            >
              <p className="ui-item-title">{entry.title}</p>
              <p className="ui-item-body">{entry.body}</p>
            </article>
          ))}
        </div>
      </section>

      <DisclosurePanel eyebrow="model ingredients" title="Genetic contributors">
        <div className="ui-section-content-grid">
          {traitDetail.rsids.map((rsid) => (
            <TeaserCard
              key={rsid.rsid}
              to={`/rsids/${rsid.rsid}`}
              eyebrow={rsid.rsid}
              title={rsid.gene ?? 'Genetic marker'}
              description={rsid.rule_description}
              footer={
                <>
                  {rsid.genotype ? (
                    <StatPill
                      label="Known genotypes"
                      value={rsid.genotype.join(', ')}
                      tooltip="Genotype patterns the current educational rule set knows how to interpret."
                      tone="accent"
                    />
                  ) : null}
                  {rsid.evidence_level ? (
                    <StatPill
                      label="Evidence"
                      value={formatEvidenceLabel(rsid.evidence_level)}
                      tooltip="Evidence level for this marker rule."
                    />
                  ) : null}
                </>
              }
            />
          ))}
        </div>
      </DisclosurePanel>

      {traitDetail.sources.length > 0 ? (
        <DisclosurePanel eyebrow="references" title="Sources">
          <div className="ui-section-content-grid">
            {traitDetail.sources.map((source) => (
              <SourceLink
                key={`${source.name}-${source.url}`}
                source={source}
              />
            ))}
          </div>
        </DisclosurePanel>
      ) : null}
    </div>
  );
}

export default TraitDetailPage;
