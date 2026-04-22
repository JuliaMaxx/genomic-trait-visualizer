import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';

import ResultToneBadge from '../components/ResultToneBadge';
import StatPill from '../components/StatPill';
import TraitDetailRsidCard from '../components/TraitDetailRsidCard';
import { useAnalysisSession } from '../context/useAnalysisSession';
import useTraitDetail from '../hooks/useTraitDetail';
import { formatConfidence } from '../utils/formatConfidence';
import { formatPercent } from '../utils/formatPercent';
import {
  formatCategoryLabel,
  formatEvidenceLabel,
} from '../utils/formatResultLabel';

function TraitDetailPage() {
  const { traitId = '' } = useParams();
  const { selectedFile } = useAnalysisSession();
  const [explanationMode, setExplanationMode] = useState<'simple' | 'technical'>(
    'simple',
  );
  const { traitDetail, errorMessage, isLoading } = useTraitDetail(
    selectedFile,
    traitId,
  );

  if (!selectedFile) {
    return <Navigate to="/" replace />;
  }

  if (!traitId) {
    return <Navigate to="/analysis" replace />;
  }

  const explanation =
    explanationMode === 'simple'
      ? traitDetail?.simple_summary
      : traitDetail?.technical_summary;

  return (
    <div className="flex flex-1 flex-col gap-grid-gap py-card-padding">
      <div className="flex flex-wrap items-center justify-between gap-grid-gap-sm">
        <div className="flex flex-wrap items-center gap-inline-gap-sm">
          <Link to="/analysis" className="ui-button-base ui-button-secondary">
            Back to overview
          </Link>
          <div className="ui-badge">trait detail page</div>
        </div>
        <p className="font-mono text-sm text-content-faint">{selectedFile.name}</p>
      </div>

      {isLoading ? (
        <div className="ui-panel">
          <p className="ui-eyebrow">loading trait detail</p>
          <p className="mt-section-offset-md text-base text-content">
            Evaluating trait-specific genotype evidence.
          </p>
        </div>
      ) : null}

      {errorMessage ? <div className="ui-panel-error">{errorMessage}</div> : null}

      {traitDetail ? (
        <>
          <section className="ui-panel-gradient">
            <div className="flex flex-wrap items-start justify-between gap-grid-gap">
              <div>
                <p className="ui-eyebrow">{formatCategoryLabel(traitDetail.category)}</p>
                <div className="mt-section-offset-sm flex flex-wrap items-center gap-inline-gap-sm">
                  <h1 className="text-3xl sm:text-4xl">{traitDetail.name}</h1>
                  <ResultToneBadge result={traitDetail.result} />
                </div>
                <p className="mt-section-offset-md max-w-(--width-text) text-base leading-body text-content-subtle">
                  {traitDetail.description}
                </p>
              </div>

              <div className="flex flex-wrap gap-inline-gap-sm">
                <StatPill label="Confidence" value={formatConfidence(traitDetail.confidence)} tone="accent" />
                <StatPill label="Coverage" value={formatPercent(traitDetail.coverage)} />
                <StatPill label="Evidence" value={formatEvidenceLabel(traitDetail.evidence_level)} />
                <StatPill label="Score" value={traitDetail.score.toFixed(2)} />
              </div>
            </div>
          </section>

          <section className="grid gap-grid-gap lg:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)]">
            <div className="ui-panel">
              <div className="flex flex-wrap items-center justify-between gap-grid-gap-sm">
                <div>
                  <p className="ui-eyebrow">progressive explanation</p>
                  <h2 className="mt-section-offset-sm text-2xl">Interpretation layer</h2>
                </div>
                <div className="flex rounded-pill border border-border bg-surface-overlay p-1">
                  <button
                    type="button"
                    onClick={() => setExplanationMode('simple')}
                    className={`rounded-pill px-badge-x py-badge-y text-sm transition ${
                      explanationMode === 'simple'
                        ? 'bg-brand text-content-inverse'
                        : 'text-content-subtle'
                    }`}
                  >
                    Simple
                  </button>
                  <button
                    type="button"
                    onClick={() => setExplanationMode('technical')}
                    className={`rounded-pill px-badge-x py-badge-y text-sm transition ${
                      explanationMode === 'technical'
                        ? 'bg-brand text-content-inverse'
                        : 'text-content-subtle'
                    }`}
                  >
                    Technical
                  </button>
                </div>
              </div>

              <div className="mt-section-offset-xl ui-panel-accent">
                <p className="ui-eyebrow text-content-accent">
                  {explanationMode === 'simple'
                    ? 'simple explanation'
                    : 'technical explanation'}
                </p>
                <p className="mt-section-offset-md text-sm leading-body text-content-muted">
                  {explanation}
                </p>
              </div>
            </div>

            <aside className="ui-panel">
              <p className="ui-eyebrow">analysis notes</p>
              <div className="mt-section-offset-lg space-y-section-offset-md">
                {traitDetail.notes.map((note) => (
                  <p key={note} className="text-sm leading-body text-content-subtle">
                    {note}
                  </p>
                ))}
              </div>

              {traitDetail.keywords.length > 0 ? (
                <div className="mt-section-offset-xl">
                  <p className="ui-eyebrow">keywords</p>
                  <div className="mt-section-offset-md flex flex-wrap gap-inline-gap-sm">
                    {traitDetail.keywords.map((keyword) => (
                      <span key={keyword} className="ui-status-pill">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
            </aside>
          </section>

          <section className="space-y-grid-gap-sm">
            <div className="flex flex-wrap items-center justify-between gap-grid-gap-sm">
              <div>
                <p className="ui-eyebrow">data layer</p>
                <h2 className="mt-section-offset-sm text-2xl">
                  rsID contribution trace
                </h2>
              </div>
              <StatPill label="Contributing rsIDs" value={String(traitDetail.rsids.length)} />
            </div>

            <div className="grid gap-grid-gap">
              {traitDetail.rsids.map((rsid) => (
                <TraitDetailRsidCard key={rsid.rsid} rsid={rsid} />
              ))}
            </div>
          </section>

          {traitDetail.sources.length > 0 ? (
            <section className="ui-panel">
              <p className="ui-eyebrow">sources</p>
              <div className="mt-section-offset-lg grid gap-grid-gap-sm md:grid-cols-2">
                {traitDetail.sources.map((source) => (
                  <a
                    key={`${source.name}-${source.url}`}
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    className="ui-panel-subtle block transition hover:border-brand-line"
                  >
                    <p className="text-sm font-semibold text-content">{source.name}</p>
                    {source.reference ? (
                      <p className="mt-section-offset-sm text-sm text-content-subtle">
                        {source.reference}
                      </p>
                    ) : null}
                    {source.notes ? (
                      <p className="mt-section-offset-sm text-sm text-content-faint">
                        {source.notes}
                      </p>
                    ) : null}
                  </a>
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export default TraitDetailPage;
