import { type ReactNode, useEffect, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';

import StatPill from '../components/StatPill';
import { fetchRsidDetail } from '../services/traitApi';
import type { RsidDetail } from '../types/analysis';
import {
  formatCategoryLabel,
  formatEvidenceLabel,
} from '../utils/formatResultLabel';

type DisclosurePanelProps = {
  title: string;
  eyebrow: string;
  children: ReactNode;
};

function DisclosurePanel({ title, eyebrow, children }: DisclosurePanelProps) {
  return (
    <section className="ui-panel">
      <details className="ui-disclosure">
        <summary className="ui-disclosure-summary">
          <div>
            <p className="ui-eyebrow">{eyebrow}</p>
            <h2 className="ui-disclosure-title">{title}</h2>
          </div>
          <span className="ui-disclosure-toggle">+</span>
        </summary>
        <div className="ui-disclosure-body">{children}</div>
      </details>
    </section>
  );
}

function scoreTone(score: number) {
  if (score > 0) {
    return 'ui-score-chip-positive';
  }
  if (score < 0) {
    return 'ui-score-chip-negative';
  }
  return 'ui-score-chip-neutral';
}

function RsidDetailPage() {
  const { rsid = '' } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<RsidDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }

    navigate('/rsids');
  };

  useEffect(() => {
    if (!rsid) {
      return;
    }

    let isCancelled = false;

    async function loadDetail() {
      setIsLoading(true);
      setErrorMessage('');

      try {
        const data = await fetchRsidDetail(rsid);
        if (!isCancelled) {
          setDetail(data);
        }
      } catch (error) {
        if (!isCancelled) {
          setDetail(null);
          setErrorMessage(
            error instanceof Error
              ? error.message
              : 'Something went wrong while loading this rsID.',
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    loadDetail();

    return () => {
      isCancelled = true;
    };
  }, [rsid]);

  if (!rsid) {
    return <Navigate to="/rsids" replace />;
  }

  return (
    <div className="ui-page-stack">
      <div className="ui-page-toolbar">
        <button
          type="button"
          className="ui-button-base ui-button-secondary"
          onClick={handleBack}
        >
          Go back
        </button>
      </div>
      {isLoading ? <div className="ui-panel">Loading rsID detail.</div> : null}

      {errorMessage ? (
        <div className="ui-panel-error">{errorMessage}</div>
      ) : null}

      {detail ? (
        <>
          <section className="ui-panel-gradient">
            <div className="ui-detail-hero-layout">
              <div className="ui-detail-hero-copy">
                <p className="ui-eyebrow">{detail.gene ?? 'genetic marker'}</p>
                <h1 className="ui-detail-title-mono">{detail.rsid}</h1>
                <p className="ui-detail-lede">{detail.technical_summary}</p>
                <p className="ui-detail-note">
                  Educational marker entry. Not medical advice; SNP effects are
                  probabilistic and research can disagree.
                </p>
                <div className="ui-pill-row-spaced">
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
            </div>
          </section>

          <section className="ui-panel">
            <p className="ui-eyebrow">technical data</p>
            <h2 className="ui-section-title">
              Rule data in the current catalog
            </h2>
            <div className="ui-section-content-equal">
              {detail.genotype_meanings.map((meaning) => (
                <div
                  key={`${meaning.genotype.join('-')}-${meaning.score}`}
                  className="ui-genotype-card"
                >
                  <div className="ui-genotype-card-header">
                    <div>
                      <p className="ui-eyebrow">genotype</p>
                      <p className="ui-genotype-value">
                        {meaning.genotype.join(' / ')}
                      </p>
                    </div>
                    <span
                      className={`ui-score-chip ${scoreTone(meaning.score)}`}
                    >
                      {meaning.score.toFixed(2)}
                    </span>
                  </div>
                  <p className="ui-feature-panel-body">{meaning.meaning}</p>
                  {meaning.effect ? (
                    <p className="ui-item-body">{meaning.effect}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </section>

          <section className="ui-panel">
            <p className="ui-eyebrow">plain English</p>
            <h2 className="ui-section-title">What this marker means</h2>
            <div className="ui-section-content">
              <div className="ui-feature-panel">
                <p className="ui-item-title">Short version</p>
                <p className="ui-feature-panel-body">
                  {detail.plain_english_summary}
                </p>
              </div>
              <div className="ui-section-content-equal">
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
                <div className="ui-section-content-equal">
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
            <div className="ui-equal-grid">
              {detail.traits.map((trait) => (
                <Link
                  key={trait.trait_id}
                  to={`/traits/${trait.trait_id}`}
                  className="ui-card-link"
                >
                  <p className="ui-eyebrow">
                    {formatCategoryLabel(trait.category)}
                  </p>
                  <h3 className="ui-card-title">{trait.trait_name}</h3>
                  <p className="ui-item-body">{trait.description}</p>
                  <div className="ui-pill-row-spaced">
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
              <div className="ui-section-content-equal">
                {detail.sources.map((source) => (
                  <a
                    key={`${source.name}-${source.url}`}
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    className="ui-panel-subtle ui-interactive-border-accent"
                  >
                    <p className="ui-item-title">{source.name}</p>
                    {source.reference ? (
                      <p className="ui-item-body">{source.reference}</p>
                    ) : null}
                    {source.notes ? (
                      <p className="ui-detail-note">{source.notes}</p>
                    ) : null}
                  </a>
                ))}
              </div>
            </DisclosurePanel>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export default RsidDetailPage;
