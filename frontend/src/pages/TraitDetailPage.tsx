import { type ReactNode, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';

import InfoTooltip from '../components/InfoTooltip';
import ResultToneBadge from '../components/ResultToneBadge';
import StatPill from '../components/StatPill';
import TraitDetailRsidCard from '../components/TraitDetailRsidCard';
import { useAnalysisSession } from '../context/useAnalysisSession';
import useTraitDetail from '../hooks/useTraitDetail';
import type { TraitRsidDetail } from '../types/analysis';
import { formatConfidence } from '../utils/formatConfidence';
import { formatPercent } from '../utils/formatPercent';
import {
  formatCategoryLabel,
  formatEvidenceLabel,
} from '../utils/formatResultLabel';

type TraitDetailPageProps = {
  mode: 'catalog' | 'analysis';
};

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

function SectionIntro({
  eyebrow,
  title,
  body,
}: {
  eyebrow: string;
  title: string;
  body?: string;
}) {
  return (
    <div>
      <p className="ui-eyebrow">{eyebrow}</p>
      <h2 className="ui-section-title">{title}</h2>
      {body ? <p className="ui-section-copy">{body}</p> : null}
    </div>
  );
}

function CatalogRsidCard({ rsid }: { rsid: TraitRsidDetail }) {
  return (
    <Link to={`/rsids/${rsid.rsid}`} key={rsid.rsid} className="ui-card-link">
      <div className="ui-card-header-stack">
        <div>
          <div className="ui-mono-link">{rsid.rsid}</div>
          <h3 className="ui-card-title">{rsid.gene ?? 'Genetic marker'}</h3>
        </div>
        <div className="ui-pill-row mb-section-offset-sm">
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
        </div>
      </div>
      <p className="ui-item-body">{rsid.rule_description}</p>
    </Link>
  );
}

function CatalogTraitView({
  traitDetail,
}: {
  traitDetail: NonNullable<ReturnType<typeof useTraitDetail>['traitDetail']>;
}) {
  const practicalTakeaways = traitDetail.practical_takeaway;
  const keywords = traitDetail.keywords.filter(
    (keyword) => keyword.trim().length > 0,
  );
  const [explanationMode, setExplanationMode] = useState<
    'simple' | 'technical'
  >('simple');

  return (
    <>
      <section className="ui-panel-gradient">
        <div className="ui-detail-hero-layout ui-detail-hero-layout-single">
          <div className="ui-detail-hero-copy">
            <p className="ui-eyebrow">
              {formatCategoryLabel(traitDetail.category)}
            </p>
            <h1 className="ui-detail-title">{traitDetail.name}</h1>
            <p className="ui-detail-lede-lg">{traitDetail.simple_summary}</p>
            <p className="ui-detail-body">{traitDetail.description}</p>
            <p className="ui-detail-note">
              Educational catalog entry. Not medical advice; effects are
              probabilistic and may vary across studies or populations.
            </p>
            <div className="ui-pill-row-spaced">
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
            {keywords.length > 0 ? (
              <div className="mt-section-offset-xl">
                <p className="ui-eyebrow">keywords</p>
                <div className="mt-section-offset-sm flex flex-wrap gap-inline-gap-compact">
                  {keywords.map((keyword, index) => (
                    <span key={`${keyword}-${index}`} className="ui-small-pill">
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
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
                ? 'friendly view'
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
          <p className="ui-eyebrow">everyday context</p>
          <h2 className="mt-section-offset-sm text-2xl">
            Useful ways to think about it
          </h2>
          <div className="mt-section-offset-xl grid gap-grid-gap-sm">
            {practicalTakeaways.map((entry) => (
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

      <section className="ui-panel-gradient border-brand-line">
        <SectionIntro
          eyebrow="research spotlight"
          title="Research spotlight"
          body="Selected context from the curated sources behind this trait."
        />
        <div className="ui-section-content-equal">
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
        <div className="ui-equal-grid">
          {traitDetail.rsids.map((rsid) => (
            <CatalogRsidCard rsid={rsid} />
          ))}
        </div>
      </DisclosurePanel>

      {traitDetail.sources.length > 0 ? (
        <DisclosurePanel eyebrow="references" title="Sources">
          <div className="ui-section-content-equal">
            {traitDetail.sources.map((source) => (
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
  );
}

function AnalysisTraitView({
  traitDetail,
  selectedFile,
}: {
  traitDetail: NonNullable<ReturnType<typeof useTraitDetail>['traitDetail']>;
  selectedFile: File;
}) {
  const observedCount = traitDetail.rsids.filter(
    (rsid) => rsid.user_genotype !== null,
  ).length;
  const matchedCount = traitDetail.rsids.filter(
    (rsid) => rsid.status === 'matched',
  ).length;

  return (
    <>
      <div className="ui-page-toolbar">
        <div>
          <Link
            to="/analysis"
            className="ui-button-base ui-button-secondary mr-badge-x"
          >
            Back to analysis
          </Link>
          <Link
            to={`/traits/${traitDetail.id}`}
            className="ui-detail-action ui-button-base ui-button-secondary"
          >
            See full trait breakdown
          </Link>
        </div>
        <p className="ui-file-label">{selectedFile.name}</p>
      </div>

      <section className="ui-panel-gradient">
        <div className="ui-detail-hero-copy">
          <p className="ui-eyebrow">
            {formatCategoryLabel(traitDetail.category)}
          </p>
          <div className="ui-pill-row-spaced">
            <span className="ui-badge">{traitDetail.name}</span>
            <ResultToneBadge
              result={traitDetail.result}
              tooltip={traitDetail.result_badge_tooltip}
            />
          </div>
          <div className="ui-heading-row">
            <h1 className="ui-detail-title">{traitDetail.headline}</h1>
            <InfoTooltip content={traitDetail.headline_tooltip} />
          </div>
          <p className="ui-detail-lede-lg">{traitDetail.outcome_summary}</p>
          <p className="ui-detail-body">
            This view is based only on markers found in your uploaded file. It
            is educational, not medical advice.
          </p>
        </div>

        <div className="ui-pill-row-spaced">
          <StatPill
            label="Confidence"
            value={formatConfidence(traitDetail.confidence)}
            tone="accent"
            tooltip="Confidence combines data completeness and evidence strength. It is not certainty."
          />
          <StatPill
            label="Coverage"
            value={formatPercent(traitDetail.coverage)}
            tooltip="Coverage tells you what share of this trait's rsIDs were available in your file."
          />
          <StatPill
            label="Score"
            value={traitDetail.score.toFixed(2)}
            tooltip="Combined direction of matched genotype rules."
          />
          <StatPill
            label="Observed rsIDs"
            value={String(observedCount)}
            tooltip="Trait model rsIDs present in your uploaded file."
          />
          <StatPill
            label="Matched rules"
            value={String(matchedCount)}
            tooltip="Observed rsIDs where your genotype matched a curated interpretation."
          />
        </div>
      </section>

      {traitDetail.practical_takeaway.length > 0 ? (
        <section className="ui-panel">
          <p className="ui-eyebrow">practical takeaways</p>
          <h2 className="ui-section-title">What this result is useful for</h2>
          <div className="ui-section-content-equal">
            {traitDetail.practical_takeaway.map((entry) => (
              <article key={entry.title} className="ui-panel-subtle">
                <p className="ui-item-title">{entry.title}</p>
                <p className="ui-item-body">{entry.body}</p>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="ui-panel">
        <p className="ui-eyebrow">your marker trace</p>
        <h2 className="ui-section-title">How your file was read</h2>
        <div className="ui-section-content-grid">
          {traitDetail.rsids.map((rsid) => (
            <TraitDetailRsidCard key={rsid.rsid} rsid={rsid} />
          ))}
        </div>
      </section>

      <DisclosurePanel
        eyebrow="calculation details"
        title="How the result formed"
      >
        <div className="ui-flow-row">
          <div className="ui-flow-step-flex">
            <p className="ui-item-title">Observed markers</p>
            <p className="ui-item-body">
              {observedCount} out of {traitDetail.rsids.length}
            </p>
          </div>
          <span className="ui-flow-arrow-responsive">-&gt;</span>
          <div className="ui-flow-step-flex">
            <p className="ui-item-title">Weighted score</p>
            <p className="ui-item-body">{traitDetail.score.toFixed(2)}</p>
          </div>
          <span className="ui-flow-arrow-responsive">-&gt;</span>
          <div className="ui-flow-step-flex">
            <p className="ui-item-title">Confidence</p>
            <p className="ui-item-body">
              {formatConfidence(traitDetail.confidence)}
            </p>
          </div>
        </div>

        <div className="ui-section-content-equal">
          {traitDetail.calculation_summary.map((entry) => (
            <div key={entry.title} className="ui-panel-subtle">
              <p className="ui-item-title">{entry.title}</p>
              <p className="ui-item-body">{entry.body}</p>
            </div>
          ))}
        </div>
      </DisclosurePanel>

      {traitDetail.sources.length > 0 ? (
        <DisclosurePanel eyebrow="references" title="Sources">
          <div className="ui-section-content-equal">
            {traitDetail.sources.map((source) => (
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
  );
}

function TraitDetailPage({ mode }: TraitDetailPageProps) {
  const { traitId = '' } = useParams();
  const navigate = useNavigate();
  const { selectedFile } = useAnalysisSession();
  const fileForDetail = mode === 'analysis' ? selectedFile : null;
  const { traitDetail, errorMessage, isLoading } = useTraitDetail(
    fileForDetail,
    traitId,
  );
  const handleCatalogBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }

    navigate('/traits');
  };

  if (!traitId) {
    return <Navigate to="/traits" replace />;
  }

  if (mode === 'analysis' && !selectedFile) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="ui-page-stack">
      {mode === 'catalog' ? (
        <div className="ui-page-toolbar">
          <button
            type="button"
            className="ui-button-base ui-button-secondary"
            onClick={handleCatalogBack}
          >
            Go back
          </button>
        </div>
      ) : null}
      {isLoading ? (
        <div className="ui-panel">
          <p className="ui-eyebrow">loading trait detail</p>
          <p className="ui-loading-copy">Loading trait-specific evidence.</p>
        </div>
      ) : null}

      {errorMessage ? (
        <div className="ui-panel-error">{errorMessage}</div>
      ) : null}

      {traitDetail && mode === 'catalog' ? (
        <CatalogTraitView traitDetail={traitDetail} />
      ) : null}

      {traitDetail && mode === 'analysis' && selectedFile ? (
        <AnalysisTraitView
          traitDetail={traitDetail}
          selectedFile={selectedFile}
        />
      ) : null}
    </div>
  );
}

export default TraitDetailPage;
