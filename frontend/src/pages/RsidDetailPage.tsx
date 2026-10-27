import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';

import Button from '../components/Button';
import StatPill from '../components/StatPill';
import { formatEvidenceLabel } from '../utils/formatLabels';
import DisclosurePanel from '../components/DisclosurePanel';
import SourceLink from '../components/SourceLink';
import useRsidDetail from '../hooks/useRsidDetail';

function scoreTone(score: number) {
  if (score > 0) {
    return 'ui-badge-success';
  }
  if (score < 0) {
    return 'ui-badge-danger';
  }
  return 'ui-badge-warning';
}

function RsidDetailPage() {
  const { rsid = '' } = useParams();
  const navigate = useNavigate();
  const { detail, errorMessage, isLoading } = useRsidDetail(rsid);

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }

    navigate('/rsids');
  };

  if (!rsid) {
    return <Navigate to="/rsids" replace />;
  }

  if (isLoading) {
    return <div className="ui-empty-state">Loading rsID detail...</div>;
  }

  if (errorMessage) {
    return (
      <div className="ui-panel-error flex justify-between items-center">
        <p>{errorMessage}</p>
        <Button onClick={handleBack}>Go back</Button>
      </div>
    );
  }

  if (detail === null || Object.keys(detail).length === 0) {
    return (
      <div className="ui-empty-state flex justify-between items-center">
        <p>No detail available for this rsID.</p>
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
            <p className="ui-eyebrow">{detail.gene ?? 'genetic marker'}</p>
            <h1 className="ui-detail-title">{detail.rsid}</h1>
            <p className="ui-detail-lede">{detail.technical_summary}</p>
            <p className="ui-detail-note">
              Educational marker entry. Not medical advice; SNP effects are
              probabilistic and research can disagree.
            </p>
          </div>
          <div className="ui-pill-collection">
            <StatPill
              label="Gene / region"
              value={detail.gene ?? 'Not specified'}
              tooltip="Gene or region linked to this rsID in the catalog."
              tone="accent"
            />
            <StatPill
              label="Linked traits"
              value={String(detail.traits.length)}
              tooltip="Number of trait models that reference this rsID."
            />
            <StatPill
              label="Genotypes"
              value={String(detail.genotype_meanings.length)}
              tooltip="Count of curated genotype interpretations for this rsID."
            />
            <StatPill
              label="Sources"
              value={String(detail.sources.length)}
              tooltip="Number of source cards linked to this rsID."
            />
          </div>
        </div>
      </section>

      <section className="mt-lg ui-panel">
        <p className="ui-eyebrow">technical data</p>
        <h2 className="ui-section-title">Rule data in the current catalog</h2>
        <div className="ui-section-content-grid">
          {detail.genotype_meanings.map((meaning) => (
            <div
              key={`${meaning.genotype.join('-')}-${meaning.score}`}
              className="ui-panel"
            >
              <div className="flex flex-wrap items-start justify-between gap-sm">
                <div>
                  <p className="ui-eyebrow">genotype</p>
                  <p className="ui-paragraph-strong mt-2xs">
                    {meaning.genotype.join(' / ')}
                  </p>
                </div>
                <span className={`ui-result-badge ${scoreTone(meaning.score)}`}>
                  {meaning.score.toFixed(2)}
                </span>
              </div>
              <p className="mt-2xs ui-paragraph-muted">{meaning.meaning}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="ui-panel">
        <p className="ui-eyebrow">plain English</p>
        <h2 className="ui-section-title">What this marker means</h2>
        <div className="mt-lg">
          <div className="ui-panel-accent">
            <p className="ui-item-title">Short version</p>
            <p className="ui-item-body text-content">
              {detail.plain_english_summary}
            </p>
          </div>
          <div className="ui-section-content-grid">
            <div className="ui-panel-subtle">
              <p className="ui-item-title">Rule description</p>
              <p className="ui-item-body">{detail.description}</p>
            </div>
            {detail.story_sections.slice(0, 1).map((section) => (
              <div key={section.title} className="ui-panel-subtle">
                <p className="ui-item-title">{section.title}</p>
                <p className="ui-item-body">{section.body}</p>
              </div>
            ))}
          </div>
          {detail.interpretation_notes.length > 0 ? (
            <div className="ui-section-content-grid">
              {detail.interpretation_notes.slice(0, 2).map((section) => (
                <div key={section.title} className="ui-panel-subtle">
                  <p className="ui-item-title">{section.title}</p>
                  <p className="ui-item-body">{section.body}</p>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      <DisclosurePanel eyebrow="cross-links" title="Traits using this SNP">
        <div className="ui-section-content-grid">
          {detail.traits.map((trait) => (
            <Link
              key={trait.trait_id}
              to={`/traits/${trait.trait_id}`}
              className="group ui-card-link"
            >
              <p className="ui-eyebrow">{trait.category}</p>
              <h3 className="ui-card-link-heading">{trait.trait_name}</h3>
              <p className="ui-item-body">{trait.description}</p>
              <div className="ui-pill-collection">
                {trait.evidence_level ? (
                  <StatPill
                    label="Evidence"
                    value={formatEvidenceLabel(trait.evidence_level)}
                    tooltip="Evidence level for this marker inside the linked trait model."
                    tone="accent"
                  />
                ) : null}
                {trait.effect ? (
                  <StatPill
                    label="Effect"
                    value={trait.effect}
                    tone="accent"
                    tooltip="Effect direction recorded in the curated rule set."
                  />
                ) : null}
              </div>
            </Link>
          ))}
        </div>
      </DisclosurePanel>

      {detail.sources.length > 0 ? (
        <DisclosurePanel eyebrow="references" title="Sources">
          <div className="ui-section-content-grid">
            {detail.sources.map((source) => (
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

export default RsidDetailPage;
