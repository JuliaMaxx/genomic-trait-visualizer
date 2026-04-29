import { type ReactNode, useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';

import InfoTooltip from '../components/InfoTooltip';
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

type DisclosurePanelProps = {
  title: string;
  eyebrow: string;
  children: ReactNode;
  panelStyle?: 'default' | 'accent' | 'subtle';
};

function DisclosurePanel({
  title,
  eyebrow,
  children,
  panelStyle = 'default',
}: DisclosurePanelProps) {
  return (
    <section className={`ui-panel ui-panel-${panelStyle}`}>
      <details className="group">
        <summary className="ui-disclosure-summary">
          <div>
            <p className="ui-eyebrow">{eyebrow}</p>
            <h2 className="mt-section-offset-sm text-2xl">{title}</h2>
          </div>
          <span className="ui-status-pill transition duration-200 group-open:rotate-45">
            +
          </span>
        </summary>
        <div className="mt-section-offset-xl">{children}</div>
      </details>
    </section>
  );
}

function TraitDetailPage() {
  const { traitId = '' } = useParams();
  const { selectedFile } = useAnalysisSession();
  const [explanationMode, setExplanationMode] = useState<
    'simple' | 'technical'
  >('simple');
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

  const observedCount =
    traitDetail?.rsids.filter((rsid) => rsid.user_genotype !== null).length ??
    0;
  const matchedCount =
    traitDetail?.rsids.filter((rsid) => rsid.status === 'matched').length ?? 0;

  return (
    <div className="flex flex-1 flex-col gap-grid-gap py-card-padding">
      <div className="flex flex-wrap items-center justify-between gap-grid-gap-sm">
        <div className="flex flex-wrap items-center gap-inline-gap-sm">
          <Link to="/analysis" className="ui-button-base ui-button-secondary">
            Back to overview
          </Link>
          <div className="ui-badge">trait detail page</div>
        </div>
        <p className="font-mono text-sm text-content-faint">
          {selectedFile.name}
        </p>
      </div>

      {isLoading ? (
        <div className="ui-panel">
          <p className="ui-eyebrow">loading trait detail</p>
          <p className="mt-section-offset-md text-base text-content">
            Evaluating trait-specific genotype evidence.
          </p>
        </div>
      ) : null}

      {errorMessage ? (
        <div className="ui-panel-error">{errorMessage}</div>
      ) : null}

      {traitDetail ? (
        <>
          <section className="ui-panel-gradient">
            <div className="flex flex-wrap items-start justify-between gap-grid-gap">
              <div className="max-w-(--width-text)">
                <p className="ui-eyebrow">
                  {formatCategoryLabel(traitDetail.category)}
                </p>
                <div className="mt-section-offset-sm flex flex-wrap items-center gap-inline-gap-sm">
                  <span className="ui-badge">{traitDetail.name}</span>
                  <ResultToneBadge
                    result={traitDetail.result}
                    tooltip={traitDetail.result_badge_tooltip}
                  />
                </div>
                <div className="mt-section-offset-lg flex flex-wrap items-start gap-inline-gap-sm">
                  <h1 className="max-w-(--width-text) text-3xl font-semibold leading-tight text-content-accent sm:text-4xl">
                    {traitDetail.headline}
                  </h1>
                  <InfoTooltip content={traitDetail.headline_tooltip} />
                </div>
                <p className="mt-section-offset-md text-base leading-body text-content-subtle">
                  {traitDetail.description}
                </p>
                <p className="mt-section-offset-lg text-lg leading-body text-content">
                  {traitDetail.outcome_summary}
                </p>
              </div>

              <div className="flex flex-wrap gap-inline-gap-sm">
                <StatPill
                  label="Confidence"
                  value={formatConfidence(traitDetail.confidence)}
                  tone="accent"
                  tooltip="Confidence tells you how dependable this educational result is. It is based on how much trait data was found in your file and how strong the curated evidence is."
                />
                <StatPill
                  label="Coverage"
                  value={formatPercent(traitDetail.coverage)}
                  tooltip="Coverage tells you what share of this trait's rsIDs were actually available in your uploaded DNA file."
                />
                <StatPill
                  label="Evidence"
                  value={formatEvidenceLabel(traitDetail.evidence_level)}
                  tooltip="Evidence describes how strong the overall research support is for this simplified trait model."
                />
                <StatPill
                  label="Score"
                  value={traitDetail.score.toFixed(2)}
                  tooltip="Score is the combined direction of all matched genotype rules. Positive values lean toward the trait, negative values lean away."
                />
                <StatPill
                  label="Observed rsIDs"
                  value={String(observedCount)}
                  tooltip="Observed rsIDs are the ones from this trait model that were actually present in your uploaded DNA file."
                />
                <StatPill
                  label="Matched rules"
                  value={String(matchedCount)}
                  tooltip="Matched rules are the observed rsIDs where your genotype matched one of the curated interpretations used by the model."
                />
              </div>
            </div>
          </section>

          <section className="mt-section-offset-xl grid gap-grid-gap-sm md:grid-cols-2">
            <div className="ui-panel">
              <div className="flex flex-wrap items-center justify-between gap-grid-gap-sm">
                <div>
                  <p className="ui-eyebrow">trait field guide</p>
                  <h2 className="mt-section-offset-sm text-2xl">
                    Interpretation layer
                  </h2>
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

              <div className="mt-section-offset-xl ui-panel-accent">
                <p className="ui-eyebrow text-content-accent">
                  {explanationMode === 'simple'
                    ? 'reader-friendly view'
                    : 'technical view'}
                </p>
                <div className="mt-section-offset-xl grid gap-grid-gap-sm">
                  {(explanationMode === 'simple'
                    ? traitDetail.simple_explanation
                    : traitDetail.technical_explanation
                  ).map((entry) => (
                    <div key={entry.title} className="ui-panel-subtle">
                      <p className="text-sm font-semibold text-content">
                        {entry.title}
                      </p>
                      <p className="mt-section-offset-sm text-sm leading-body text-content-subtle">
                        {entry.body}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="ui-panel">
              <p className="ui-eyebrow">personal relevance</p>
              <h2 className="mt-section-offset-sm text-2xl">
                What should I do with this?
              </h2>
              <div className="mt-section-offset-xl grid gap-grid-gap-sm">
                {traitDetail.practical_takeaway.map((entry) => (
                  <div key={entry.title} className="ui-panel-subtle">
                    <p className="text-sm font-semibold text-content">
                      {entry.title}
                    </p>
                    <p className="mt-section-offset-sm text-sm leading-body text-content-subtle">
                      {entry.body}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <DisclosurePanel eyebrow="deep dive" title="Research spotlight">
            <div className="mt-section-offset-xl grid gap-grid-gap-sm md:grid-cols-2">
              {traitDetail.research_spotlight.map((item) => (
                <div key={item.title} className="ui-panel-subtle">
                  <p className="text-sm font-semibold text-content">
                    {item.title}
                  </p>
                  <p className="mt-section-offset-sm text-sm leading-body text-content-subtle">
                    {item.body}
                  </p>
                </div>
              ))}
            </div>
          </DisclosurePanel>

          <DisclosurePanel
            eyebrow="transparency layer"
            title="But how did you actually calculate this?"
          >
            <div className="flex flex-wrap items-stretch gap-inline-gap-sm">
              <div className="ui-flow-step min-w-40 flex-1">
                <p className="text-sm font-semibold text-content">
                  Observed markers
                </p>
                <p className="mt-section-offset-sm text-sm text-content-subtle">
                  {observedCount} out of {traitDetail.rsids.length}
                </p>
              </div>
              <span className="ui-flow-arrow hidden md:inline">=&gt;</span>
              <div className="ui-flow-step min-w-40 flex-1">
                <p className="text-sm font-semibold text-content">
                  Weighted score
                </p>
                <p className="mt-section-offset-sm text-sm text-content-subtle">
                  {traitDetail.score.toFixed(2)}
                </p>
              </div>
              <span className="ui-flow-arrow hidden md:inline">-&gt;</span>
              <div className="ui-flow-step min-w-40 flex-1">
                <p className="text-sm font-semibold text-content">
                  Final confidence
                </p>
                <p className="mt-section-offset-sm text-sm text-content-subtle">
                  {formatConfidence(traitDetail.confidence)}
                </p>
              </div>
            </div>

            <div className="mt-section-offset-lg ui-panel-accent">
              <p className="ui-eyebrow text-content-accent">formula snapshot</p>
              <p className="mt-section-offset-sm text-sm leading-body text-content">
                Score = normalized weighted sum of matched marker effects.
                Confidence = coverage x evidence-strength modifier.
              </p>
            </div>

            <div className="mt-section-offset-xl grid gap-grid-gap-sm md:grid-cols-2">
              {traitDetail.calculation_summary.map((entry) => (
                <div key={entry.title} className="ui-panel-subtle">
                  <p className="text-sm font-semibold text-content">
                    {entry.title}
                  </p>
                  <p className="mt-section-offset-sm text-sm leading-body text-content-subtle">
                    {entry.body}
                  </p>
                </div>
              ))}
            </div>
          </DisclosurePanel>

          <DisclosurePanel eyebrow="data layer" title="rsID-by-rsID trace">
            <StatPill
              label="rsIDs in model"
              value={String(traitDetail.rsids.length)}
              tooltip="This is the total number of rsIDs the current trait model uses."
            />
            <div className="mt-section-offset-lg grid gap-grid-gap">
              {traitDetail.rsids.map((rsid) => (
                <TraitDetailRsidCard key={rsid.rsid} rsid={rsid} />
              ))}
            </div>
          </DisclosurePanel>

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
                    className="ui-panel-subtle ui-interactive-panel-link"
                  >
                    <p className="text-sm font-semibold text-content">
                      {source.name}
                    </p>
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
