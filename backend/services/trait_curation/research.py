"""Research-to-dossier handoff. Generated records carry no review decisions."""

import json
import os
import re
import shutil
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from backend.models.curation import (
    AssessedClaim,
    ClaimType,
    EvidenceClaim,
    EvidenceLocation,
    EvidenceSource,
    ExplanationContent,
    ExtractionMethod,
    SourceType,
    TraitCandidate,
    TraitDossier,
)
from backend.models.research import (
    Extraction,
    NormalizedRecord,
    RawRecord,
    ResearchRun,
    SavedResponse,
)
from backend.services.trait_curation.compiler import (
    SourceDocument,
    sha256,
    source_documents,
    stable_json,
)
from backend.services.trait_curation.preview import _plain_text
from backend.services.trait_curation.research_extract import (
    extract,
    normalize,
    reported_qualifiers,
    source_location,
)
from backend.services.trait_curation.workflow import read_workspace, write_json_new


def acquisition_root(path: Path) -> Path:
    """Accept an acquisition directory or a proposal linked by relative metadata."""
    if (path / "run.json").is_file():
        return path
    metadata_path = path / "processing.json"
    if not metadata_path.is_file():
        raise ValueError(
            f"No acquisition run.json or proposal processing.json in {path}"
        )
    metadata = json.loads(metadata_path.read_bytes())
    if not isinstance(metadata, dict):
        raise ValueError("Proposal processing.json must contain a JSON object")
    relative = metadata.get("acquisition_run")
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("Proposal needs a relative acquisition_run in processing.json")
    root = (path / relative).resolve()
    run_path = root / "run.json"
    if not run_path.is_file():
        raise ValueError(f"Saved acquisition run missing: {run_path}")
    if sha256(run_path.read_bytes()) != metadata.get("run_sha256"):
        raise ValueError("Proposal acquisition run hash mismatch")
    return root


def load_run(root: Path) -> ResearchRun:
    root = acquisition_root(root)
    run = ResearchRun.model_validate_json((root / "run.json").read_bytes())
    for response in run.responses:
        if response.path is None:
            if response.error is None:
                raise ValueError(f"Missing saved response: {response.document_id}")
            continue
        path = (root / response.path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Response path escapes the research run")
        if not path.is_file():
            raise ValueError(f"Saved source missing: {response.document_id} at {path}")
        if sha256(path.read_bytes()) != response.sha256:
            raise ValueError(f"Source hash mismatch: {response.document_id}")
    return run


def verify_research_acquisition(
    workspace: Path,
    inventory_path: Path | None,
) -> list[SourceDocument] | None:
    """Verify Stage 5 inputs against the run hash captured by the first review.

    Manual Stage 4 workspaces have no research origin and keep their old path.
    This checks local consistency, not external scientific authenticity.
    """
    snapshots, _ = read_workspace(workspace)
    initial, current = snapshots[0].dossier, snapshots[-1].dossier
    expected_hash = initial.candidate.research_run_sha256
    research = any(
        snapshot.dossier.candidate.pipeline_version.startswith("stage5-")
        or snapshot.dossier.candidate.research_run_sha256 is not None
        for snapshot in snapshots
    )
    if not research:
        return None
    if expected_hash is None:
        raise ValueError(
            "Stage 5 workspace has no reviewed acquisition-run hash; replay the "
            "saved run into a new proposal and import it into a new review workspace."
        )
    if current.candidate.research_run_sha256 != expected_hash:
        raise ValueError("Reviewed Stage 5 acquisition-run identity changed")
    if inventory_path is None:
        raise ValueError(
            "Stage 5 finalization requires --acquisition <proposal/acquisition.json>"
        )
    metadata = json.loads((inventory_path.parent / "processing.json").read_bytes())
    if not isinstance(metadata, dict):
        raise ValueError("Proposal processing.json must contain a JSON object")
    if metadata.get("run_sha256") != expected_hash:
        raise ValueError("Acquisition run does not match the reviewed Stage 5 origin")
    root = acquisition_root(inventory_path.parent)
    run = load_run(root)
    if sha256((root / "run.json").read_bytes()) != expected_hash:
        raise ValueError("Reviewed acquisition run hash mismatch")
    responses = {item.document_id: item for item in run.responses}
    records = extract(root, run).records
    acquired = {record.record_id: responses[record.document_id] for record in records}

    evidence_ids = {ref for claim in current.claims for ref in claim.evidence_ids}
    published_sources = {
        ref
        for item in current.evidence
        if item.evidence_id in evidence_ids
        for ref in item.source_ids
    }
    # Reuse Stage 4's list/type/uniqueness and selected-source completeness checks.
    documents = source_documents(inventory_path, published_sources)
    # The calling build/approval/publication services require effective Stage 3
    # decisions, which cover source metadata through its evidence dependency.
    referenced_sources = {ref for item in current.evidence for ref in item.source_ids}
    supplemental = {
        source.source_id
        for source in current.sources
        if source.source_id not in acquired and source.source_id in referenced_sources
    }
    inventory = json.loads(inventory_path.read_bytes())
    seen: set[str] = set()
    for row in inventory:
        source_id = row.get("source_id")
        response = acquired.get(source_id) if isinstance(source_id, str) else None
        if isinstance(source_id, str) and source_id in supplemental:
            # Preserve Stage 4's manual original/excerpt and multi-document shape.
            SourceDocument.model_validate(
                {key: row[key] for key in SourceDocument.model_fields if key in row}
            )
            continue
        if (
            response is None
            or source_id in seen
            or row.get("document_id") != source_id
            or row.get("sha256") != response.sha256
            or row.get("url") != response.url
            or row.get("path") != response.path
            or row.get("type") != "original"
            or row.get("path_base") != "processing.json#/acquisition_run"
        ):
            raise ValueError(
                f"Acquisition inventory disagrees with retained source: {source_id}"
            )
        seen.add(source_id)
    for source in current.sources:
        if source.source_id in supplemental:
            continue
        response = acquired.get(source.source_id)
        if (
            response is None
            or source.url != response.url
            or source.source_version != f"sha256:{response.sha256}"
        ):
            raise ValueError(
                "Dossier source disagrees with verified acquisition: "
                f"{source.source_id}"
            )
    return documents


def _values(normalized: NormalizedRecord) -> dict[str, Any]:
    return {field.field: field.proposed_value for field in normalized.fields}


def _source(record: RawRecord, response: SavedResponse) -> EvidenceSource:
    data: dict[str, Any] = {
        "source_id": record.record_id,
        "source_type": SourceType.ASSOCIATION_DATABASE,
        "name": "NHGRI-EBI GWAS Catalog",
        "url": response.url,
        "source_version": f"sha256:{response.sha256}",
        "retrieved_at": response.retrieved_at,
    }
    pmid = str(record.fields.get("pubmed_id", record.fields.get("pmid", "")))
    if pmid.isdigit():
        data["pmid"] = pmid
    if record.kind == "publication":
        data.update(source_type=SourceType.SCIENTIFIC_PUBLICATION, name="Europe PMC")
        for field in ("title", "doi", "pmcid"):
            if record.fields.get(field):
                data[field] = record.fields[field]
        year = str(record.fields.get("pubYear", ""))
        if year.isdigit():
            data["publication_year"] = int(year)
    return EvidenceSource.model_validate(data)


def _p_value(values: dict[str, Any]) -> str | None:
    """Format reported components exactly; never guess missing or conflicting ones."""
    reported = values.get("p_value")
    mantissa = values.get("pvalue_mantissa")
    exponent = values.get("pvalue_exponent")
    if mantissa is None and exponent is None:
        return (
            str(reported)
            if reported is not None
            and type(reported) in (int, float)
            and 0 < reported <= 1
            else None
        )
    # The supported API reports both components as integers. Do not coerce them.
    if type(mantissa) is not int or type(exponent) is not int:
        return None
    exact = f"{mantissa}e{exponent}"
    if not 0 < Decimal(exact) <= 1:
        return None
    if reported is None:
        return exact
    # Float conversion is only a consistency check against the API's rounded
    # number. The displayed underflowed value always uses the original components.
    if type(reported) not in (int, float) or float(exact) != reported:
        return None
    return exact if reported == 0 else str(reported)


def _statement(record: RawRecord, values: dict[str, Any]) -> str:
    if record.kind == "association":
        marker = values["rsid"] or "an unresolved variant/haplotype"
        phenotype = values["phenotype"] or "an unresolved phenotype"
        statement = (
            f"GWAS Catalog lists {marker} in an association record for {phenotype!r}."
        )
        p_value = _p_value(values)
        if p_value is not None:
            statement += f" Reported p_value: {p_value}."
        elif any(
            values.get(name) is not None
            for name in ("p_value", "pvalue_mantissa", "pvalue_exponent")
        ):
            statement += (
                " P-value unresolved: source fields are incomplete, invalid or "
                "inconsistent; review the retained reported values."
            )
        for name in ("beta", "or_value", "or_per_copy_num", "range"):
            value = values.get(name)
            if value is not None and value not in ("", "-", "NR", "NA", "?"):
                statement += f" Reported {name}: {value}."
        return statement
    if record.kind == "study":
        statement = f"GWAS Catalog study {values['accession_id']}"
        if values.get("disease_trait"):
            statement += f" studies {values['disease_trait']!r}"
        statement += "."
        if values.get("initial_sample_size"):
            statement += (
                f" Discovery sample as reported: {values['initial_sample_size']}."
            )
        if values.get("replication_sample_size"):
            statement += (
                f" Replication sample as reported: {values['replication_sample_size']}."
            )
        return statement
    title = values.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Publication has no title; no bibliographic claim drafted")
    year = values.get("pubYear", "year unresolved")
    return f"Europe PMC identifies PMID {values['pmid']} as {title!r} ({year})."


def make_dossier(
    run: ResearchRun, extraction: Extraction, normalized: list[NormalizedRecord]
) -> TraitDossier:
    identifier = re.sub(r"[^a-z0-9]+", "_", run.request.trait_name.lower()).strip("_")[
        :80
    ]
    if not identifier:
        identifier = "trait_" + sha256(run.request.trait_name.encode())[:12]
    candidate = TraitCandidate(
        candidate_id=f"research-{identifier}",
        proposed_id=identifier,
        proposed_name=run.request.trait_name,
        keywords=run.search_terms,
        pipeline_version="stage5-v10",
        description=(
            f"Research proposals for {run.request.trait_name}. "
            "Scientific relevance and a trait-level explanation await human review."
        ),
        created_at=run.started_at,
        reviewer_notes=[
            "Automatic proposals only. Review relevance, fields and wording."
        ],
    )
    dossier = TraitDossier(candidate=candidate)
    responses = {response.document_id: response for response in run.responses}
    proposals = {proposal.record_id: proposal for proposal in normalized}
    for record in extraction.records:
        proposal = proposals[record.record_id]
        values = _values(proposal)
        limitations = proposal.unresolved + reported_qualifiers(record)
        try:
            source = _source(record, responses[record.document_id])
            statement = _statement(record, values)
            claim_type = (
                ClaimType.TRAIT_ASSOCIATION
                if record.kind == "association"
                else ClaimType.OTHER
            )
            evidence = EvidenceClaim(
                evidence_id=f"e-{record.record_id}",
                trait_id=identifier,
                claim_type=claim_type,
                statement=statement,
                rsid=values.get("rsid"),
                phenotype=values.get("phenotype"),
                effect_allele=values.get("effect_allele"),
                effect_direction=(
                    values.get("beta_direction")
                    if values.get("beta_direction") in ("increase", "decrease")
                    else None
                ),
                source_ids=[record.record_id],
                source_location=EvidenceLocation(locator=source_location(record)),
                extraction_method=ExtractionMethod.STRUCTURED_API,
                extractor_version="stage5-v10",
                extracted_at=run.completed_at,
                validation_notes=limitations,
            )
            claim = AssessedClaim(
                claim_id=f"c-{record.record_id}",
                claim_type=claim_type,
                statement=statement,
                evidence_ids=[evidence.evidence_id],
                scope=(
                    "Description of this retrieved database record only; "
                    "relevance is unassessed."
                ),
                limitations=limitations,
            )
        except ValueError as exc:
            extraction.warnings.append(
                f"{record.record_id}: dossier proposal withheld: {exc}"
            )
            continue
        dossier.sources.append(source)
        dossier.evidence.append(evidence)
        dossier.claims.append(claim)
    dossier.candidate.source_ids = [source.source_id for source in dossier.sources]
    dossier.candidate.evidence_ids = [
        evidence.evidence_id for evidence in dossier.evidence
    ]
    # Population and bibliography are dependencies of the association's claim.
    available = set(dossier.candidate.evidence_ids)
    records = {record.record_id: record for record in extraction.records}
    for claim in dossier.claims:
        record = records[claim.claim_id.removeprefix("c-")]
        if record.kind == "association":
            study_id = f"gwas-study-{record.fields.get('accession_id')}"
            study = records.get(study_id)
            study_ref = f"e-{study_id}"
            if study is not None and study_ref in available:
                association_pmid = str(record.fields.get("pubmed_id", ""))
                study_pmid = str(study.fields.get("pubmed_id", ""))
                if (
                    association_pmid.isdigit()
                    and study_pmid.isdigit()
                    and association_pmid != study_pmid
                ):
                    note = (
                        "Conflicting association/study PMIDs: "
                        f"{source_location(record, 'pubmed_id')} "
                        f"reports {association_pmid}; "
                        f"{source_location(study, 'pubmed_id')} reports {study_pmid}. "
                        "Study context not attached to this association."
                    )
                    claim.limitations.append(note)
                    next(
                        item
                        for item in dossier.evidence
                        if item.evidence_id == f"e-{record.record_id}"
                    ).validation_notes.append(note)
                    extraction.warnings.append(note)
                else:
                    claim.evidence_ids.append(study_ref)
                    claim.limitations.extend(reported_qualifiers(study))
                    if not association_pmid.isdigit() or not study_pmid.isdigit():
                        claim.limitations.append(
                            "Study linked by accession only; "
                            "a missing/unsupported PMID "
                            "prevents independent publication-identity comparison."
                        )
            for ref in (f"e-europe-pmc-MED-{record.fields.get('pubmed_id')}",):
                if ref in available:
                    claim.evidence_ids.append(ref)
    return TraitDossier.model_validate(dossier.model_dump(mode="json"))


def draft_explanations(dossier: TraitDossier) -> list[dict[str, Any]]:
    """Draft reported findings by explicit references; no abstract paraphrasing."""
    bindings: list[dict[str, Any]] = []
    evidence_by_id = {item.evidence_id: item for item in dossier.evidence}
    sources = {item.source_id: item for item in dossier.sources}
    for claim in dossier.claims:
        findings = [evidence_by_id[ref] for ref in claim.evidence_ids]
        associations = [
            item for item in findings if item.claim_type == ClaimType.TRAIT_ASSOCIATION
        ]
        # Study/publication references provide context to an association, rather
        # than silently selecting an unrelated item by its list position.
        primary = associations or findings
        study_context = []
        for item in findings:
            if any(
                source_id.startswith("gwas-study-") for source_id in item.source_ids
            ):
                study_context.append(item.statement)
                study_context.extend(
                    note
                    for note in item.validation_notes
                    if note.startswith("Source-reported ")
                    and note not in claim.limitations
                )
        for evidence in primary:
            drafts: list[tuple[str, str, str]]
            if evidence.claim_type == ClaimType.TRAIT_ASSOCIATION:
                marker = evidence.rsid or "an unresolved marker"
                trait = evidence.phenotype or "an unresolved phenotype"
                allele = evidence.effect_allele or "unresolved"
                direction = evidence.effect_direction or "unresolved"
                marker_details = (
                    f"Marker: {marker}. Reported effect allele: {allele}. "
                    f"Reported effect direction: {direction}."
                )
                drafts = [
                    (
                        "description",
                        "Association description (pending)",
                        f"Retrieved association for {trait!r}. " + marker_details,
                    ),
                    (
                        "simple_summary",
                        "Study finding (pending)",
                        f"The catalog reports a link between {marker} and {trait!r}. "
                        f"The reported effect allele is {allele}; "
                        "personal applicability needs review.",
                    ),
                    (
                        "technical_summary",
                        "Reported measurements",
                        evidence.statement + " These are source-reported measurements, "
                        "not application coefficients.",
                    ),
                    (
                        "simple_explanation",
                        "Research marker tooltip",
                        marker_details
                        + " The effect allele is reported study notation; "
                        "genomic orientation remains unresolved.",
                    ),
                    (
                        "technical_explanation",
                        "Genetic marker context",
                        marker_details
                        + " This record concerns "
                        + repr(trait)
                        + ". No causal mechanism or genotype-to-outcome mapping "
                        "was extracted.",
                    ),
                    (
                        "practical_takeaway",
                        "Applicability and limitations",
                        "This finding requires scientific review. "
                        + "\n".join(claim.limitations),
                    ),
                ]
            else:
                publication = next(
                    (
                        sources[ref]
                        for ref in evidence.source_ids
                        if sources[ref].source_type == SourceType.SCIENTIFIC_PUBLICATION
                    ),
                    None,
                )
                body = evidence.statement
                if publication is not None:
                    if publication.doi:
                        body += f" DOI: {publication.doi}."
                    if publication.pmcid:
                        body += f" PMCID: {publication.pmcid}."
                    body += (
                        " Bibliographic candidate only. Read the saved abstract "
                        "using the source location in review.md. "
                        "No scientific conclusion, mechanism or genetic association "
                        "has been extracted from the title or abstract."
                    )
                drafts = [("research_spotlight", "Source context (pending)", body)]
            for kind, title, body in drafts:
                if associations and study_context:
                    body += "\n\nLinked study context (as reported):\n" + "\n".join(
                        study_context
                    )
                conditions = [
                    item
                    for item in claim.limitations
                    if item.startswith(
                        (
                            "Source-reported ",
                            "Background traits ",
                            "Conflicting association/study ",
                            "Study linked by accession only",
                        )
                    )
                ]
                if conditions and kind != "practical_takeaway":
                    body += "\n\nReported study conditions (require review):\n"
                    body += "\n".join(conditions)
                content = ExplanationContent.model_validate(
                    {
                        "content_id": f"{kind}-{claim.claim_id}-{evidence.evidence_id}",
                        "kind": kind,
                        "title": title,
                        "body": body,
                        "claim_ids": [claim.claim_id],
                    }
                )
                dossier.explanations.append(content)
                bindings.append(
                    {
                        "content_id": content.content_id,
                        "evidence_ids": claim.evidence_ids,
                        "template": f"stage5-templates-v8/{kind}",
                        "input_statements": {
                            item.evidence_id: item.statement for item in findings
                        },
                        "source_locations": {
                            item.evidence_id: item.source_location.model_dump(
                                exclude_none=True
                            )
                            for item in findings
                        },
                    }
                )
    return bindings


def _cell(value: object) -> str:
    text = (
        value
        if isinstance(value, str) and value
        else json.dumps(value, ensure_ascii=False)
    )
    return _plain_text(text).replace("\n", "<br>")


def review_report(
    run: ResearchRun,
    extraction: Extraction,
    normalized: list[NormalizedRecord],
    dossier: TraitDossier,
) -> str:
    records = extraction.records + extraction.ontology_candidates
    responses = {response.document_id: response for response in run.responses}
    proposals = {item.record_id: item for item in normalized}
    evidence = {item.evidence_id: item for item in dossier.evidence}
    claims = {item.claim_id: item for item in dossier.claims}
    notes_by_record = {}
    for record in records:
        notes = list(proposals[record.record_id].unresolved)
        claim = claims.get(f"c-{record.record_id}")
        if claim:
            notes.extend(claim.limitations)
        # Reported qualifiers appear in the value tables, including linked context.
        notes_by_record[record.record_id] = list(
            dict.fromkeys(
                note for note in notes if not note.startswith("Source-reported ")
            )
        )
    note_counts = Counter(note for notes in notes_by_record.values() for note in notes)
    lines = [
        f"# Research proposals: {_plain_text(run.request.trait_name)}",
        "",
        "**Pending review. Search relevance is not verified evidence.**",
        "",
        "Terms: " + ", ".join(_plain_text(term) for term in run.search_terms),
        "",
        f"Retrieved sources: {len(dossier.sources)} | "
        f"Evidence proposals: {len(dossier.evidence)} | "
        f"Draft explanations: {len(dossier.explanations)}",
        "",
        "No interpretation, category, scientific approvals "
        "or expected cases were generated.",
        "",
        "Full draft wording is in [dossier.json](dossier.json); "
        "[drafting.json](drafting.json) records its evidence bindings. "
        "Drafts are pending review and are not repeated under linked sources.",
        "",
    ]
    report_fields = {
        "association": (
            "snp_allele",
            "snp_effect_allele",
            "mapped_genes",
            "locations",
            "reported_trait",
            "bg_efo_traits",
            "p_value",
            "pvalue_mantissa",
            "pvalue_exponent",
            "pvalue_description",
            "beta",
            "beta_num",
            "beta_unit",
            "beta_direction",
            "or_value",
            "or_per_copy_num",
            "range",
            "ci_lower",
            "ci_upper",
            "risk_frequency",
            "description",
            "multi_snp_haplotype",
            "snp_interaction",
        ),
        "study": (
            "initial_sample_size",
            "replication_sample_size",
            "discovery_ancestry",
            "replication_ancestry",
            "bg_efo_traits",
            "gxe",
            "gxg",
        ),
        "publication": ("doi", "pmcid", "authorString"),
        "ontology": ("efo_id", "efo_trait"),
    }
    for heading, kinds in (
        ("Findings", {"association"}),
        ("Study and publication context", {"study", "publication"}),
        ("Search candidates", {"ontology"}),
    ):
        group = [record for record in records if record.kind in kinds]
        if not group:
            continue
        lines.extend([f"## {heading}", ""])
        for record in group:
            proposal = proposals[record.record_id]
            values = _values(proposal)
            finding = evidence.get(f"e-{record.record_id}")
            claim = claims.get(f"c-{record.record_id}")
            title = (
                f"{values.get('rsid') or 'Unresolved marker'}: "
                f"{values.get('phenotype') or 'unresolved phenotype'}"
                if record.kind == "association"
                else record.record_id
            )
            lines.extend([f"### {_plain_text(title)}", ""])
            if finding:
                lines.extend([_plain_text(finding.statement), ""])
            else:
                lines.extend(
                    ["No evidence proposal; retained for inspection only.", ""]
                )
            if record.kind == "association":
                allele = values.get("effect_allele") or "unresolved"
                direction = (
                    finding.effect_direction if finding else None
                ) or "unresolved"
                lines.extend(
                    [
                        f"Proposed effect allele: {_plain_text(allele)}; "
                        f"effect direction: {_plain_text(direction)}.",
                        "",
                    ]
                )
            references = [
                f"{key}: {_cell(record.fields[key])}"
                for key in ("accession_id", "pubmed_id", "pmid")
                if key in record.fields
            ]
            if references:
                lines.extend(["References: " + "; ".join(references), ""])
            lines.extend(
                [
                    "Source record: "
                    + _plain_text(record.record_id)
                    + " at "
                    + _plain_text(source_location(record)),
                    "",
                ]
            )
            if claim:
                lines.extend(
                    [
                        "Evidence: "
                        + _plain_text(f"e-{record.record_id}")
                        + " | Claim: "
                        + _plain_text(claim.claim_id),
                        "",
                    ]
                )
                context = [
                    ref for ref in claim.evidence_ids if ref != f"e-{record.record_id}"
                ]
                if context:
                    lines.extend(
                        [
                            "Linked context (shown once below): "
                            + _plain_text(", ".join(context)),
                            "",
                        ]
                    )
            fields = [
                field
                for field in proposal.fields
                if field.field in report_fields[record.kind]
            ]
            if fields:
                lines.extend(
                    ["| Reported field | Source-reported value |", "| --- | --- |"]
                )
                lines.extend(
                    f"| {_cell(field.field)} | {_cell(field.reported_value)} |"
                    for field in fields
                )
                lines.append("")
            lines.extend(
                "- " + _plain_text(note)
                for note in notes_by_record[record.record_id]
                if note_counts[note] == 1
            )
            lines.append("")
            if record.kind == "publication" and record.fields.get("abstractText"):
                lines.extend(
                    [
                        "Abstract reading context (not an extracted conclusion): "
                        + _plain_text(source_location(record, "abstractText"))
                        + "; not interpreted or reproduced here.",
                        "",
                    ]
                )
            if record.kind == "ontology":
                lines.extend(
                    ["Found by: " + _plain_text("; ".join(record.found_by)), ""]
                )
    lines.extend(["## Shared limitations", ""])
    lines.extend(
        "- " + _plain_text(note) for note, count in note_counts.items() if count > 1
    )
    lines.extend(
        [
            "",
            "## Source files and full details",
            "",
            "Response paths are relative to the acquisition run identified by "
            "[processing.json](processing.json)'s acquisition_run. "
            "Its run.json retains queries, retrieval failures and SHA-256 hashes.",
            "",
            "| Response | Source URL | Saved response |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| {_cell(response.document_id)} | {_cell(response.url)} | "
        f"{_cell(response.path or 'not saved')} |"
        for response in responses.values()
    )
    lines.extend(
        [
            "",
            "[raw-extraction.json](raw-extraction.json) preserves extracted values "
            "and discovery reasons; [normalized.json](normalized.json) records "
            "exact field locations, proposed values and transformations. "
            "[acquisition.json](acquisition.json) lists publication source documents.",
            "",
        ]
    )
    lines.extend(["## Warnings and failures", ""])
    warnings = list(dict.fromkeys(run.warnings + extraction.warnings))
    lines.extend("- " + _plain_text(warning) for warning in warnings)
    if not warnings:
        lines.append("No retrieval or extraction warnings recorded.")
    lines.extend(
        [
            "",
            "## Review proposed information",
            "",
            "Import dossier.json with init into a new review workspace. "
            "Use inspect, revise and decide to check sources, correct drafts and "
            "record decisions. See curation/stage3-review.md "
            "in the repository for command examples.",
            "A reviewer must supply a category, justified interpretation and "
            "independent expected cases before building a publication candidate. "
            "Use finalize with --cases and --acquisition acquisition.json to "
            "inspect the preview and explicitly confirm publication.",
        ]
    )
    return "\n".join(lines) + "\n"


def replay(root: Path, destination: Path) -> TraitDossier:
    """Regenerate deterministic first-pass files without any network access."""
    tick = time.perf_counter()
    root = acquisition_root(root)
    run = load_run(root)
    try:
        relative_run = Path(os.path.relpath(root, destination)).as_posix()
        bundle_acquisition = False
    except ValueError:
        # Windows cannot express relative paths between drives. Keep a portable
        # copy of just the run and its retained responses inside the new proposal.
        relative_run, bundle_acquisition = "acquisition", True
    extraction = extract(root, run)
    normalized = [
        normalize(record)
        for record in extraction.records + extraction.ontology_candidates
    ]
    dossier = make_dossier(run, extraction, normalized)
    dossier.candidate.research_run_sha256 = sha256((root / "run.json").read_bytes())
    bindings = draft_explanations(dossier)
    dossier = TraitDossier.model_validate(dossier.model_dump(mode="json"))
    responses = {response.document_id: response for response in run.responses}
    included = {source.source_id for source in dossier.sources}
    inventory = [
        {
            "document_id": record.record_id,
            "source_id": record.record_id,
            "sha256": responses[record.document_id].sha256,
            "url": responses[record.document_id].url,
            "type": "original",
            "version": "stage5-v10",
            "path": responses[record.document_id].path,
            "path_base": "processing.json#/acquisition_run",
        }
        for record in extraction.records
        if record.record_id in included
    ]
    artifacts = {
        "raw-extraction.json": stable_json(extraction.model_dump(mode="json")),
        "normalized.json": stable_json(
            [item.model_dump(mode="json") for item in normalized]
        ),
        "dossier.json": stable_json(dossier.model_dump(mode="json")),
        "drafting.json": stable_json(
            {
                "method": "templates",
                "version": "stage5-templates-v8",
                "model": None,
                "bindings": bindings,
            }
        ),
        "acquisition.json": stable_json(inventory),
        "review.md": review_report(run, extraction, normalized, dossier).encode(
            "utf-8"
        ),
    }
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in artifacts.items():
        with (destination / name).open("xb") as stream:
            stream.write(raw)
    if bundle_acquisition:
        bundled = destination / relative_run
        bundled.mkdir()
        shutil.copyfile(root / "run.json", bundled / "run.json")
        for response in run.responses:
            if response.path:
                target = bundled / response.path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / response.path, target)
    write_json_new(
        destination / "processing.json",
        {
            "extractor_version": "stage5-v10",
            "drafting_version": "stage5-templates-v8",
            "acquisition_run": relative_run,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.perf_counter() - tick, 6),
            "run_sha256": sha256((root / "run.json").read_bytes()),
            "initial_output_sha256": {
                name: sha256(raw) for name, raw in artifacts.items()
            },
        },
    )
    return dossier
