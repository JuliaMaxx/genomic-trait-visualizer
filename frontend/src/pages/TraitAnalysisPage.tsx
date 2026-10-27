import { Navigate, useNavigate, useParams } from 'react-router-dom';

import ResultToneBadge from '../components/ResultToneBadge';
import LinkButton from '../components/LinkButton';
import StatPill from '../components/StatPill';
import TraitDetailRsidCard from '../components/TraitDetailRsidCard';
import { useAnalysisSession } from '../context/useAnalysisSession';
import { formatConfidence } from '../utils/formatConfidence';
import { formatPercent } from '../utils/formatPercent';
import DisclosurePanel from '../components/DisclosurePanel';
import Button from '../components/Button';
import SourceLink from '../components/SourceLink';
import useTraitDetailAnalysis from '../hooks/useTraitDetailAnalysis';

function TraitAnalysisPage() {
  const { traitId = '' } = useParams();
  const { selectedFile } = useAnalysisSession();
  const navigate = useNavigate();
  const fileForDetail = selectedFile;
  const { traitDetail, errorMessage, isLoading } = useTraitDetailAnalysis(
    fileForDetail,
    traitId,
  );

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }

    navigate('/analysis');
  };

  if (!traitId) {
    return <Navigate to="/analysis" replace />;
  }

  if (!selectedFile) {
    return <Navigate to="/" replace />;
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

  const observedCount = traitDetail.rsids.filter(
    (rsid) => rsid.user_genotype !== null,
  ).length;
  const matchedCount = traitDetail.rsids.filter(
    (rsid) => rsid.status === 'matched',
  ).length;

  return (
    <div className="ui-page-stack">
      <div className="ui-page-toolbar">
        <div>
          <Button
            type="button"
            variant="secondary"
            onClick={handleBack}
            className="mr-sm"
          >
            Go back
          </Button>
          <LinkButton to={`/traits/${traitDetail.id}`} variant="secondary">
            See full trait breakdown
          </LinkButton>
        </div>
        <p className="ui-paragraph-faint">{selectedFile.name}</p>
      </div>

      <section className="ui-panel-gradient">
        <div className="flex justify-start items-center gap-md">
          <p className="ui-eyebrow">{traitDetail.category}</p>
          <ResultToneBadge
            result={traitDetail.result}
            tooltip={traitDetail.result_badge_tooltip}
          />
        </div>
        <div className="ui-detail-hero-layout">
          <div>
            <h1 className="ui-detail-title">{traitDetail.headline}</h1>
            <p className="ui-detail-lede-lg">{traitDetail.outcome_summary}</p>
            <p className="ui-detail-note">
              This view is based only on markers found in your uploaded file. It
              is educational, not medical advice.
            </p>
          </div>
          <div className="ui-pill-collection">
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
        </div>
      </section>

      {traitDetail.practical_takeaway.length > 0 ? (
        <section className="ui-panel  border-brand-line">
          <p className="ui-eyebrow">practical takeaways</p>
          <h2 className="ui-section-title">What this result is useful for</h2>
          <div className="ui-section-content-grid">
            {traitDetail.practical_takeaway.map((entry) => (
              <article key={entry.title} className="ui-panel-subtle">
                <p className="ui-item-title">{entry.title}</p>
                <p className="ui-item-body">{entry.body}</p>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <DisclosurePanel
        eyebrow="your marker trace"
        title="How your file was read"
      >
        <div className="ui-section-content-stack">
          {traitDetail.rsids.map((rsid) => (
            <TraitDetailRsidCard key={rsid.rsid} rsid={rsid} />
          ))}
        </div>
      </DisclosurePanel>

      <DisclosurePanel
        eyebrow="calculation details"
        title="How the result formed"
      >
        <div className="flex-wrap items-center gap-sm hidden md:flex">
          <div className="ui-flow-step">
            <p className="ui-item-title">Observed markers</p>
            <p className="ui-item-body-brand">
              {observedCount} out of {traitDetail.rsids.length}
            </p>
          </div>
          <span className="ui-flow-arrow">-&gt;</span>
          <div className="ui-flow-step">
            <p className="ui-item-title">Weighted score</p>
            <p className="ui-item-body-brand">{traitDetail.score.toFixed(2)}</p>
          </div>
          <span className="ui-flow-arrow">-&gt;</span>
          <div className="ui-flow-step">
            <p className="ui-item-title">Confidence</p>
            <p className="ui-item-body-brand">
              {formatConfidence(traitDetail.confidence)}
            </p>
          </div>
        </div>

        <div className="ui-section-content-grid">
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

export default TraitAnalysisPage;
