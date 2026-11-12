"""Offline Stage 5 acceptance; all review decisions here are fictional."""

import json
import shutil
from copy import deepcopy
from html import unescape
from http.client import BadStatusLine, IncompleteRead
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import mistune
import pytest
from pydantic import ValidationError

from backend.models.curation import ReviewAction
from backend.models.research import ResearchRequest, SourceRegistry
from backend.services.trait_curation import research_sources
from backend.services.trait_curation.cli import main
from backend.services.trait_curation.compiler import (
    build_candidate,
    sha256,
    source_documents,
    stable_json,
)
from backend.services.trait_curation.research import (
    acquisition_root,
    draft_explanations,
    load_run,
    replay,
    review_report,
    verify_research_acquisition,
)
from backend.services.trait_curation.research_extract import (
    extract,
    normalize,
    source_location,
)
from backend.services.trait_curation.research_sources import (
    REGISTRY,
    acquire,
    collection,
    search_terms,
)
from backend.services.trait_curation.workflow import (
    ReviewScope,
    get_snapshot,
    initialize_workspace,
    inspect_item,
    record_decision,
    revise_workspace,
    workspace_history,
    workspace_status,
)

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "curation/examples"
FROZEN = EXAMPLES / "stage5-lactose-search"


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Stage 5 tests must never contact scientific APIs")

    monkeypatch.setattr(research_sources, "urlopen", blocked)


def recorded_network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    responses = {
        response.url: (response.status_code, (FROZEN / response.path).read_bytes())
        for response in load_run(FROZEN).responses
        if response.path is not None
    }
    called: list[str] = []

    def fetch(url: str) -> tuple[int, bytes]:
        called.append(url)
        if parse_qs(urlsplit(url).query).get("query", [""])[0].startswith("TITLE_ABS:"):
            return 200, b'{"resultList":{"result":[]}}'
        code, raw = responses[url]
        assert code is not None
        return code, raw

    monkeypatch.setattr(research_sources, "fetch", fetch)
    return called


def decide(
    workspace: Path,
    scope: ReviewScope,
    target: str,
    action: ReviewAction = ReviewAction.APPROVE,
) -> None:
    inspected = inspect_item(get_snapshot(workspace).dossier, scope, target)
    record_decision(
        workspace,
        scope,
        target,
        action,
        "synthetic-test-reviewer",
        "Fictional workflow test only, not a scientific assessment.",
        inspected["revision"],
        inspected["fingerprint"],
    )


def test_trait_queries_and_limits() -> None:
    registry = SourceRegistry.model_validate_json(REGISTRY.read_bytes())
    request = ResearchRequest(
        trait_name="Lactose Digestion Ability", synonyms=[" lactose tolerance test "]
    )
    assert search_terms(request, registry) == [
        "Lactose Digestion Ability",
        "lactose tolerance test",
    ]
    assert search_terms(ResearchRequest(trait_name="Unknown trait"), registry) == [
        "Unknown trait"
    ]
    for change in (
        {"limit": 0},
        {"limit": 11},
        {"trait_name": " "},
        {"synonyms": [""]},
        {"synonyms": ["a"] * 5},
    ):
        with pytest.raises(ValidationError):
            ResearchRequest.model_validate({"trait_name": "Trait", **change})
    combined = ResearchRequest(
        trait_name="Lactose Digestion Ability", synonyms=["one", "two", "three", "four"]
    )
    with pytest.raises(ValueError, match="remove a --synonym.*Combined terms"):
        search_terms(combined, registry)


def test_configured_synonyms_ignore_internal_name_whitespace() -> None:
    registry = SourceRegistry.model_validate_json(REGISTRY.read_bytes())
    expected = ["Lactose Digestion Ability", "lactose tolerance test"]
    for name in (
        "Lactose Digestion Ability",
        "Lactose  Digestion Ability",
        "Lactose\tDigestion  Ability",
    ):
        assert search_terms(ResearchRequest(trait_name=name), registry) == expected


def test_acquisition_records_exact_bytes_queries_and_deduplicated_lookups(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = recorded_network(monkeypatch)
    run = acquire(
        ResearchRequest(trait_name="Lactose Digestion Ability", limit=2),
        tmp_path / "run",
    )
    assert len(called) == 7
    assert [response.kind for response in run.responses] == [
        "traits",
        "traits",
        "associations",
        "study",
        "publication",
        "literature",
        "literature",
    ]
    assert run.responses[2].parameters["efo_id"] == "EFO_0010557"
    assert run.responses[4].parameters["query"] == "EXT_ID:31791255 AND SRC:MED"
    for actual, frozen in zip(
        run.responses[:5], load_run(FROZEN).responses, strict=True
    ):
        assert actual.path and frozen.path
        assert (tmp_path / "run" / actual.path).read_bytes() == (
            FROZEN / frozen.path
        ).read_bytes()
        assert actual.sha256 == frozen.sha256
        assert actual.retrieved_at.tzinfo is not None and actual.elapsed_seconds >= 0
    assert run.acquisition_seconds >= 0
    with pytest.raises(FileExistsError):
        acquire(run.request, tmp_path / "run")


def test_frozen_scientific_fields_keep_unknowns_unresolved(tmp_path: Path) -> None:
    dossier = replay(FROZEN, tmp_path / "proposal")
    run = load_run(FROZEN)
    raw = extract(FROZEN, run)
    assert len(raw.records) == len(dossier.evidence) == 4
    first = raw.records[0]
    assert first.fields["p_value"] == 1e-6
    assert first.fields["snp_allele"] == [{"rs_id": "rs6563275", "effect_allele": "?"}]
    assert first.fields["locations"] == ["13:82218857"]
    fields = {field.field: field for field in normalize(first).fields}
    assert fields["effect_allele"].reported_value == "?"
    assert fields["effect_allele"].proposed_value is None
    assert fields["effect_allele"].source_location.endswith(
        "/snp_allele/0/effect_allele"
    )
    assert fields["beta"].reported_value == "-" and fields["beta"].proposed_value == "-"
    assert dossier.evidence[0].gene is None  # Mapped genes are not causal genes.
    assert dossier.evidence[1].rsid is None  # T-13910 is not guessed to be rs4988235.
    assert dossier.evidence[0].effect_direction is None
    assert "53 Fulani" in dossier.evidence[2].statement
    assert dossier.sources[-1].pmid == "31791255"
    assert dossier.sources[-1].publication_year == 2019


def test_generated_dossier_contains_pending_reviewable_drafts(tmp_path: Path) -> None:
    dossier = replay(FROZEN, tmp_path / "proposal")
    assert (
        dossier.interpretation is None and dossier.candidate.proposed_category is None
    )
    assert all(finding.status == "pending" for finding in dossier.evidence)
    assert all(
        claim.status == "pending" and claim.assessment is None
        for claim in dossier.claims
    )
    assert all(
        not text.reviewed and text.result_key is None for text in dossier.explanations
    )
    assert {text.kind for text in dossier.explanations} >= {
        "description",
        "simple_summary",
        "technical_summary",
        "simple_explanation",
    }
    assert "e-gwas-study-GCST009418" in dossier.claims[0].evidence_ids
    assert "e-europe-pmc-MED-31791255" in dossier.claims[0].evidence_ids
    assert "abstractText" not in (tmp_path / "proposal/dossier.json").read_text()
    report = (tmp_path / "proposal/review.md").read_text(encoding="utf-8")
    assert "T-13910" in report and "Source-reported value" in report
    assert "No genotype interpretation" in report


def test_offline_replay_is_deterministic_and_checks_source_hashes(
    tmp_path: Path,
) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    assert replay(FROZEN, first) == replay(FROZEN, second)
    metadata = json.loads((first / "processing.json").read_bytes())
    for name, digest in metadata["initial_output_sha256"].items():
        assert (first / name).read_bytes() == (second / name).read_bytes()
        assert sha256((first / name).read_bytes()) == digest
    # Preserve the v1 first pass rather than regenerating it with corrected semantics.
    original = json.loads((FROZEN / "proposal/processing.json").read_bytes())
    assert original["extractor_version"] == "stage5-v1"
    assert metadata["extractor_version"] == "stage5-v10"
    for name, digest in original["initial_output_sha256"].items():
        assert sha256((FROZEN / "proposal" / name).read_bytes()) == digest
    with pytest.raises(FileExistsError):
        replay(FROZEN, first)
    copied = tmp_path / "changed"
    shutil.copytree(FROZEN, copied)
    (copied / "responses/response-003.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="Source hash mismatch"):
        replay(copied, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_review_report_groups_findings_and_keeps_full_details_in_json(
    tmp_path: Path,
) -> None:
    output = tmp_path / "proposal"
    dossier = replay(FROZEN, output)
    run = load_run(FROZEN)
    extraction = extract(FROZEN, run)
    normalized = [
        normalize(record)
        for record in extraction.records + extraction.ontology_candidates
    ]
    inputs = [run, extraction, *normalized, dossier]
    before = [item.model_dump(mode="json") for item in inputs]
    report = unescape(review_report(run, extraction, normalized, dossier))
    assert [item.model_dump(mode="json") for item in inputs] == before
    assert len(report.splitlines()) < 220
    assert "## Findings" in report and "## Study and publication context" in report
    assert "## Review proposed information" in report
    assert "Stage 3" not in report and "Stage 4" not in report
    assert "T-13910" in report and "rs4988235" not in report
    assert "Proposed effect allele: unresolved; effect direction: unresolved." in report
    assert report.count("Genome build, allele orientation, comparison/denominator") == 1
    for finding in dossier.evidence:
        assert finding.evidence_id in report
        assert finding.source_location.locator is not None
        assert finding.source_location.locator in report
        assert report.count(finding.statement) == 1
    for response in run.responses:
        assert response.url in report
        if response.path:
            assert response.path in report
    assert all(warning in report for warning in run.warnings)
    saved = json.loads((output / "dossier.json").read_bytes())
    assert saved == dossier.model_dump(mode="json")
    for content in dossier.explanations:
        assert content.content_id not in report
        assert content.body not in report
        assert content.model_dump(mode="json") in saved["explanations"]
    for name in ("dossier.json", "drafting.json", "normalized.json", "processing.json"):
        assert f"]({name})" in report


def replace_response(root: Path, kind: str, data: dict[str, Any]) -> None:
    """Change a temporary API response while keeping the test run consistent."""
    run = load_run(root)
    response = next(item for item in run.responses if item.kind == kind)
    assert response.path is not None
    raw = stable_json(data)
    (root / response.path).write_bytes(raw)
    response.sha256 = sha256(raw)
    (root / "run.json").write_bytes(stable_json(run.model_dump(mode="json")))


def mutated_run(tmp_path: Path, rows: list[Any]) -> Path:
    copied = tmp_path / "input"
    shutil.copytree(FROZEN, copied)
    replace_response(copied, "associations", {"_embedded": {"associations": rows}})
    return copied


def associations() -> list[dict[str, Any]]:
    data = json.loads((FROZEN / "responses/response-003.json").read_bytes())
    result: list[dict[str, Any]] = data["_embedded"]["associations"]
    return result


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        ({"p_value": 0.0, "pvalue_mantissa": 3, "pvalue_exponent": -400}, "3e-400"),
        ({"pvalue_mantissa": 3, "pvalue_exponent": -400}, "3e-400"),
        (
            {"p_value": 1e-6, "pvalue_mantissa": 1, "pvalue_exponent": -6},
            "1e-06",
        ),
        ({"p_value": 1e-6}, "1e-06"),
        ({"p_value": 0.0, "pvalue_mantissa": 3}, None),
        ({"p_value": 0.0, "pvalue_exponent": -400}, None),
        ({"p_value": 3e-6, "pvalue_mantissa": 3, "pvalue_exponent": -400}, None),
        ({"p_value": 0.0, "pvalue_mantissa": 3, "pvalue_exponent": -6}, None),
        ({"p_value": 0.0}, None),
        ({"p_value": 0.0, "pvalue_mantissa": "3", "pvalue_exponent": -400}, None),
    ],
    ids=[
        "underflow",
        "components-only",
        "ordinary",
        "number-only",
        "missing-exponent",
        "missing-mantissa",
        "conflicting-number",
        "inconsistent-zero",
        "zero-without-components",
        "invalid-component",
    ],
)
def test_p_value_wording_preserves_precision_or_stays_unresolved(
    tmp_path: Path, reported: dict[str, Any], expected: str | None
) -> None:
    row = associations()[0]
    for name in ("p_value", "pvalue_mantissa", "pvalue_exponent"):
        row.pop(name, None)
    row.update(reported)
    root = mutated_run(tmp_path, [row])
    dossier = replay(root, tmp_path / "proposal")
    statement = dossier.evidence[0].statement
    if expected is None:
        assert "P-value unresolved" in statement
        assert "Reported p_value:" not in statement
    else:
        assert f"Reported p_value: {expected}." in statement
    technical = next(
        text for text in dossier.explanations if text.kind == "technical_summary"
    )
    assert dossier.claims[0].statement == statement
    assert statement in technical.body
    assert "Reported p_value: 0.0" not in technical.body


def test_underflowed_p_value_fields_remain_traceable_in_review(tmp_path: Path) -> None:
    reported = {"p_value": 0.0, "pvalue_mantissa": 3, "pvalue_exponent": -400}
    row = {**associations()[0], **reported}
    root = mutated_run(tmp_path, [row])
    source = root / "responses/response-003.json"
    original = source.read_bytes()
    record = extract(root, load_run(root)).records[0]
    fields = {field.field: field for field in normalize(record).fields}
    dossier = replay(root, tmp_path / "proposal")
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Inspect exact reported p-value fields.")
    claim = dossier.claims[0]
    inspected = inspect_item(
        get_snapshot(workspace).dossier, ReviewScope.CLAIM, claim.claim_id
    )
    technical = next(
        text for text in dossier.explanations if text.kind == "technical_summary"
    )
    for name, value in reported.items():
        field = fields[name]
        assert field.reported_value == field.proposed_value == value
        assert resolve_pointer(json.loads(original), field.source_location) == value
        note = f"Source-reported {name} ({field.source_location}): " + json.dumps(value)
        assert note in dossier.evidence[0].validation_notes
        assert note in inspected["reviewed"]["payload"]["limitations"]
        assert note in technical.body
    report = unescape((tmp_path / "proposal/review.md").read_text(encoding="utf-8"))
    assert "Reported p_value: 3e-400" in report
    assert "| p_value | 0.0 |" in report
    assert "| pvalue_mantissa | 3 |" in report
    assert "| pvalue_exponent | -400 |" in report
    assert source.read_bytes() == original


@pytest.mark.parametrize("metadata", ["[]", "null"])
def test_proposal_metadata_requires_a_json_object(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], metadata: str
) -> None:
    proposal, workspace = tmp_path / "proposal", tmp_path / "review"
    dossier = replay(FROZEN, proposal)
    initialize_workspace(workspace, dossier, "Malformed metadata regression.")
    (proposal / "processing.json").write_text(metadata, encoding="utf-8")
    message = r"processing\.json must contain a JSON object"
    with pytest.raises(ValueError, match=message):
        acquisition_root(proposal)
    with pytest.raises(ValueError, match=message):
        verify_research_acquisition(workspace, proposal / "acquisition.json")
    with pytest.raises(SystemExit) as error:
        main(["replay", str(proposal), str(tmp_path / "output")])
    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert "processing.json must contain a JSON object" in stderr
    assert "Traceback" not in stderr
    assert not (tmp_path / "output").exists()


def test_duplicate_records_merge_discovery_paths_but_conflicts_are_withheld(
    tmp_path: Path,
) -> None:
    row = associations()[0]
    root = mutated_run(tmp_path, [row, deepcopy(row)])
    records = extract(root, load_run(root)).records
    assert len([r for r in records if r.kind == "association"]) == 1
    assert len(records[0].found_by) == 2
    changed = deepcopy(row)
    changed["p_value"] = 0.04
    second = mutated_run(tmp_path / "conflict", [row, changed])
    extraction = extract(second, load_run(second))
    assert not any(r.kind == "association" for r in extraction.records)
    assert any("Conflicting duplicate" in warning for warning in extraction.warnings)


@pytest.mark.parametrize(
    "change",
    ["missing", "missing_leaf", "haplotype", "interaction", "invalid_rsid", "case"],
)
def test_narrow_normalization_never_guesses_variants(
    tmp_path: Path, change: str
) -> None:
    row = associations()[0]
    if change == "missing":
        row.pop("snp_allele")
        row.pop("reported_trait")
    elif change == "haplotype":
        row["multi_snp_haplotype"] = True
        row["snp_allele"].append({"rs_id": "rs671", "effect_allele": "A"})
    elif change == "interaction":
        row["snp_interaction"] = True
    elif change == "missing_leaf":
        row["snp_allele"][0].pop("effect_allele")
    elif change == "invalid_rsid":
        row["snp_allele"][0] = {"rs_id": "rs671?", "effect_allele": "AG"}
    else:
        row["snp_allele"][0] = {"rs_id": " RS671 ", "effect_allele": " a "}
        # Keep both representations consistent in this case-only test.
        row["snp_effect_allele"] = [" RS671 - a "]
    root = mutated_run(tmp_path, [row])
    extracted = extract(root, load_run(root)).records[0]
    proposed = {field.field: field for field in normalize(extracted).fields}
    expected_rsid = (
        "rs671"
        if change == "case"
        else ("rs6563275" if change == "missing_leaf" else None)
    )
    assert proposed["rsid"].proposed_value == expected_rsid
    assert proposed["effect_allele"].proposed_value == (
        "A" if change == "case" else None
    )
    if change == "case":
        assert proposed["rsid"].reported_value == " RS671 "
    if change == "missing":
        assert proposed["effect_allele"].source_location == (
            f"{extracted.document_id}#{extracted.locator}"
        )
    if change == "missing_leaf":
        assert proposed["effect_allele"].source_location.endswith("/snp_allele/0")
    if change == "haplotype":
        assert proposed["effect_allele"].source_location.endswith("/snp_allele")
    # Parent locations for missing values still point into the retained document.
    document = json.loads((root / "responses/response-003.json").read_bytes())
    for field in proposed.values():
        value = resolve_pointer(document, field.source_location)
        if field.reported_value is not None:
            assert value == field.reported_value
    assert "genome_build" not in proposed
    assert "rules" not in proposed and "score" not in proposed


@pytest.mark.parametrize(
    ("secondary", "expected_rsid", "expected_allele"),
    [
        (["  RS6563275 - a  "], "rs6563275", "A"),
        (["rs6563275-G"], "rs6563275", None),
        (["rs671-A"], None, None),
        (None, "rs6563275", "A"),
        (["rs671-?"], None, None),
        (["rs6563275-A", "rs671-G"], None, None),
        (["rs6563275-?"], "rs6563275", "A"),
        (["rs6563275-A", "rs671-?"], None, None),
        (["rs6563275-?", "rs6563275-A"], "rs6563275", "A"),
        (["rs6563275-A", "rs6563275-G"], "rs6563275", None),
        (["T-13910-?", "rs671-?"], None, None),
        (["T-13910-?", "rs671-A;rs6563275-A"], "rs6563275", "A"),
    ],
    ids=[
        "matching",
        "allele-conflict",
        "rsid-conflict",
        "absent",
        "unknown-allele-identity-conflict",
        "multiple-identity-conflict",
        "matching-unknown-allele",
        "multiple-unknown-allele-conflict",
        "multiple-matching-identities",
        "multiple-conflicting-alleles",
        "multiple-mixed-supported-identities",
        "multiple-unparsable-identities",
    ],
)
def test_secondary_alleles_cannot_override_or_conceal_conflicts(
    tmp_path: Path,
    secondary: list[str] | None,
    expected_rsid: str | None,
    expected_allele: str | None,
) -> None:
    row = associations()[0]
    primary = [{"rs_id": " RS6563275 ", "effect_allele": " a "}]
    row["snp_allele"] = primary
    if secondary is None:
        row.pop("snp_effect_allele")
    else:
        row["snp_effect_allele"] = secondary
    root = mutated_run(tmp_path, [row])
    dossier = replay(root, tmp_path / "proposal")
    evidence, claim = dossier.evidence[0], dossier.claims[0]
    assert evidence.rsid == expected_rsid
    assert evidence.effect_allele == expected_allele
    assert any(
        "Conflicting GWAS allele representations" in note for note in claim.limitations
    ) == (expected_allele is None)
    if secondary and any("T-13910" in value for value in secondary):
        assert any("unsupported or ambiguous" in note for note in claim.limitations)
    if expected_rsid is None:
        assert "rs6563275" not in claim.statement
        assert not any(
            "Marker: rs6563275" in text.body
            for text in dossier.explanations
            if claim.claim_id in text.claim_ids
        )


def test_conflicting_alleles_preserve_originals_and_reach_review(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    row = associations()[0]
    row["snp_allele"] = [{"rs_id": " RS6563275 ", "effect_allele": " a "}]
    row["snp_effect_allele"] = ["rs6563275-G"]
    root = mutated_run(tmp_path, [row])
    source = root / "responses/response-003.json"
    original = source.read_bytes()
    record = extract(root, load_run(root)).records[0]
    fields = {field.field: field for field in normalize(record).fields}
    for name in ("snp_allele", "snp_effect_allele"):
        field = fields[name]
        assert field.reported_value == field.proposed_value == row[name]
        assert resolve_pointer(json.loads(original), field.source_location) == row[name]
    dossier = replay(root, tmp_path / "proposal")
    claim = dossier.claims[0]
    inspected = inspect_item(dossier, ReviewScope.CLAIM, claim.claim_id)
    note = next(
        note for note in claim.limitations if note.startswith("Conflicting GWAS")
    )
    assert "response-003#/_embedded/associations/0/snp_allele" in note
    assert "response-003#/_embedded/associations/0/snp_effect_allele" in note
    assert note in inspected["reviewed"]["payload"]["limitations"]
    texts = [
        text.body for text in dossier.explanations if claim.claim_id in text.claim_ids
    ]
    assert texts and any("unresolved" in text for text in texts)
    assert not any(
        "Reported effect allele: A" in text or "reported effect allele is A" in text
        for text in texts
    )
    assert "p_value: 1e-06" in dossier.evidence[0].statement
    report = unescape((tmp_path / "proposal/review.md").read_text(encoding="utf-8"))
    assert note in report
    assert "Proposed effect allele: unresolved" in report
    assert "rs6563275-G" in report and '"effect_allele": " a "' in report
    assert main(["replay", str(root), str(tmp_path / "conflict-replay")]) == 0
    summary = capsys.readouterr().out
    assert (
        "Warning: 1 finding(s) have conflicting source values; see report." in summary
    )
    assert "Conflicting GWAS allele representations:" not in summary
    assert source.read_bytes() == original


@pytest.mark.parametrize("secondary", ["rs671-A", "rs671-?", "rs671-"])
def test_conflicting_rsid_is_withheld_even_if_primary_allele_is_unknown(
    tmp_path: Path,
    secondary: str,
) -> None:
    row = associations()[0]  # Its primary effect allele is explicitly unknown (?).
    row["snp_effect_allele"] = [secondary]
    root = mutated_run(tmp_path, [row])
    dossier = replay(root, tmp_path / "proposal")
    assert dossier.evidence[0].rsid is None
    assert dossier.evidence[0].effect_allele is None
    assert any(
        "marker identities disagree" in note
        for note in dossier.evidence[0].validation_notes
    )


def resolve_pointer(document: Any, location: str) -> Any:
    pointer = location.split("#", 1)[1]
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        document = (
            document[int(token)] if isinstance(document, list) else document[token]
        )
    return document


def test_association_qualifiers_and_statistics_reach_review_and_drafts(
    tmp_path: Path,
) -> None:
    context = {
        "pvalue_description": "females, smokers",
        "description": "Discovery cohort only",
        "bg_efo_traits": [
            {"efo_id": "EFO_9999999", "efo_trait": "Fictional condition"}
        ],
        "beta_num": -0.25,
        "beta_unit": "mg / dL",
        "ci_lower": -0.5,
        "ci_upper": 0.0,
    }
    row = associations()[0]
    row.update(context)
    row.pop("beta")
    row.pop("range")
    root = mutated_run(tmp_path, [row])
    record = extract(root, load_run(root)).records[0]
    fields = {field.field: field for field in normalize(record).fields}
    dossier = replay(root, tmp_path / "proposal")
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Inspect reported association context.")
    claim = dossier.claims[0]
    inspected = inspect_item(
        get_snapshot(workspace).dossier, ReviewScope.CLAIM, claim.claim_id
    )
    texts = [text for text in dossier.explanations if claim.claim_id in text.claim_ids]
    assert texts
    report = unescape((tmp_path / "proposal/review.md").read_text(encoding="utf-8"))
    document = json.loads((root / "responses/response-003.json").read_bytes())
    for name, value in context.items():
        field = fields[name]
        assert field.reported_value == field.proposed_value == value
        assert resolve_pointer(document, field.source_location) == value
        note = f"Source-reported {name} ({field.source_location}): " + json.dumps(value)
        assert note in dossier.evidence[0].validation_notes
        assert note in inspected["reviewed"]["payload"]["limitations"]
        assert all(note in text.body for text in texts)
        assert f"| {name} |" in report
        assert (value if isinstance(value, str) else json.dumps(value)) in report
    assert all(
        "not causation or individual applicability" in text.body for text in texts
    )
    assert dossier.candidate.description is not None
    assert "Discovery cohort only" not in dossier.candidate.description
    unqualified = replay(FROZEN, tmp_path / "unqualified")
    assert not any(
        note.startswith(tuple(f"Source-reported {name} " for name in context))
        for note in unqualified.claims[0].limitations
    )


@pytest.mark.parametrize("interaction", [True, False])
def test_study_context_reaches_review_and_linked_drafts(
    tmp_path: Path, interaction: bool
) -> None:
    root = mutated_run(tmp_path, [associations()[0]])
    data = json.loads((root / "responses/response-004.json").read_bytes())
    context = {
        "discovery_ancestry": ["125 Fictional discovery participants"],
        "replication_ancestry": ["47 Fictional replication participants"],
        "gxe": interaction,
        "gxg": interaction,
        "bg_efo_traits": [
            {"efo_id": "EFO_9999999", "efo_trait": "Fictional condition"}
        ],
    }
    data.update(context)
    replace_response(root, "study", data)
    record = next(r for r in extract(root, load_run(root)).records if r.kind == "study")
    fields = {field.field: field for field in normalize(record).fields}
    dossier = replay(root, tmp_path / "proposal")
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Inspect reported study context.")
    reviewed = get_snapshot(workspace).dossier
    study = next(
        e for e in reviewed.evidence if e.evidence_id == "e-gwas-study-GCST009418"
    )
    claims = [
        claim for claim in reviewed.claims if study.evidence_id in claim.evidence_ids
    ]
    assert len(claims) == 2  # The study and its linked association.
    report = unescape((tmp_path / "proposal/review.md").read_text(encoding="utf-8"))
    for name, value in context.items():
        field = fields[name]
        assert field.reported_value == field.proposed_value == value
        assert resolve_pointer(data, field.source_location) == value
        note = f"Source-reported {name} ({field.source_location}): " + json.dumps(value)
        assert note in study.validation_notes
        assert f"| {name} |" in report
        assert json.dumps(value) in report
        for claim in claims:
            inspected = inspect_item(reviewed, ReviewScope.CLAIM, claim.claim_id)
            assert note in inspected["reviewed"]["payload"]["limitations"]
            texts = [
                text
                for text in reviewed.explanations
                if claim.claim_id in text.claim_ids
            ]
            assert texts and all(note in text.body for text in texts)
    assert all(
        "not causation or individual applicability" in text.body
        for text in reviewed.explanations
        if reviewed.claims[0].claim_id in text.claim_ids
    )


@pytest.mark.parametrize("background", [[], None], ids=["empty", "absent"])
def test_missing_study_context_is_not_invented(
    tmp_path: Path, background: list[Any] | None
) -> None:
    root = mutated_run(tmp_path, [associations()[0]])
    data = json.loads((root / "responses/response-004.json").read_bytes())
    names = (
        "discovery_ancestry",
        "replication_ancestry",
        "gxe",
        "gxg",
        "bg_efo_traits",
    )
    for name in names:
        data.pop(name, None)
    if background is not None:
        data["bg_efo_traits"] = background
    replace_response(root, "study", data)
    record = next(r for r in extract(root, load_run(root)).records if r.kind == "study")
    fields = {field.field: field for field in normalize(record).fields}
    if background is None:
        assert "bg_efo_traits" not in fields
    else:
        assert (
            fields["bg_efo_traits"].reported_value
            == fields["bg_efo_traits"].proposed_value
            == []
        )
    dossier = replay(root, tmp_path / "proposal")
    prefixes = tuple(f"Source-reported {name} " for name in names)
    assert not any(
        note.startswith(prefixes)
        for claim in dossier.claims
        for note in claim.limitations
    )
    assert not any(
        prefix in text.body for prefix in prefixes for text in dossier.explanations
    )


@pytest.mark.parametrize("failure", ["incomplete", "bad_status"])
def test_interrupted_body_preserves_run_and_cli_can_replay_successes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    frozen = load_run(FROZEN)
    replies = {
        r.url: (FROZEN / r.path).read_bytes() for r in frozen.responses if r.path
    }

    def open_response(request: Any, **kwargs: Any) -> Any:
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        if "/studies/" in request.full_url:
            response.read.side_effect = (
                IncompleteRead(b'{"accession_id":', 20)
                if failure == "incomplete"
                else BadStatusLine("Interrupted protocol")
            )
        else:
            response.read.return_value = replies.get(
                request.full_url, b'{"resultList":{"result":[]}}'
            )
        return response

    monkeypatch.setattr(research_sources, "urlopen", open_response)
    root = tmp_path / "run"
    assert (
        main(["research", "Lactose Digestion Ability", str(root), "--limit", "2"]) == 0
    )
    run = load_run(root)
    failed = run.responses[3]
    assert len(run.responses) == 7
    assert failed.kind == "study" and failed.status_code == 200
    assert (
        failed.error
        and ("IncompleteRead" if failure == "incomplete" else "BadStatusLine")
        in failed.error
    )
    assert failed.url.endswith("/studies/GCST009418") and failed.parameters == {}
    assert failed.path is None and failed.sha256 is None
    assert not (root / "responses/response-004.json").exists()
    assert run.responses[2].sha256 == frozen.responses[2].sha256
    dossier = replay(root, tmp_path / "replay")
    assert (
        len(dossier.evidence) == 3
    )  # Two associations and the successful PMID lookup.
    assert not any("gwas-study" in e.evidence_id for e in dossier.evidence)
    assert "Retrieval failed" in capsys.readouterr().out


def test_proposal_paths_resolve_after_moving_with_acquisition(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    run_root = bundle / "acquisition"
    shutil.copytree(FROZEN, run_root)
    proposal = bundle / "proposals" / "review"
    dossier = replay(run_root, proposal)
    metadata = json.loads((proposal / "processing.json").read_bytes())
    assert metadata["acquisition_run"] == "../../acquisition"
    inventory = json.loads((proposal / "acquisition.json").read_bytes())
    for row in inventory:
        assert row["path_base"] == "processing.json#/acquisition_run"
        assert (
            sha256((acquisition_root(proposal) / row["path"]).read_bytes())
            == row["sha256"]
        )
    # Operational paths are ignored by the existing Stage 4 scientific projection.
    documents = source_documents(
        proposal / "acquisition.json", {s.source_id for s in dossier.sources}
    )
    assert all("path" not in document.model_dump() for document in documents)
    moved = tmp_path / "relocated"
    bundle.rename(moved)
    relocated_proposal = moved / "proposals/review"
    assert acquisition_root(relocated_proposal) == (moved / "acquisition").resolve()
    assert replay(relocated_proposal, moved / "replayed") == dossier
    (moved / "acquisition/responses/response-003.json").unlink()
    with pytest.raises(ValueError, match="Saved source missing: response-003"):
        replay(relocated_proposal, tmp_path / "missing")


def test_malformed_associations_do_not_discard_neighbors_or_break_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, second = associations()
    beyond_limit = {**second, "association_id": 999}
    rows = [
        first,
        {"association_id": 123, "efo_traits": None},
        None,
        deepcopy(first),
        second,
        beyond_limit,
    ]
    root = mutated_run(tmp_path / "offline", rows)
    extraction = extract(root, load_run(root))
    records = [record for record in extraction.records if record.kind == "association"]
    assert [record.record_id for record in records] == [
        "gwas-association-55467061",
        "gwas-association-55467053",
    ]
    assert len(records[0].found_by) == 2
    assert any(
        "record 1" in warning and "malformed efo_traits" in warning
        for warning in extraction.warnings
    )
    assert any("record 2" in warning for warning in extraction.warnings)
    recorded_network(monkeypatch)
    original_fetch = research_sources.fetch

    def fetch(url: str) -> tuple[int, bytes]:
        if "/associations?" in url:
            return 200, stable_json({"_embedded": {"associations": rows}})
        return original_fetch(url)

    monkeypatch.setattr(research_sources, "fetch", fetch)
    acquired = tmp_path / "acquired"
    run = acquire(
        ResearchRequest(trait_name="Lactose Digestion Ability", limit=2), acquired
    )
    assert any("record 1 skipped" in warning for warning in run.warnings)
    assert len(replay(acquired, acquired / "proposal").evidence) == 4


def test_field_specific_missing_values_and_pointer_escaping(tmp_path: Path) -> None:
    row = associations()[0]
    row.update(beta_direction="-", description="NR")
    root = mutated_run(tmp_path, [row])
    record = extract(root, load_run(root)).records[0]
    proposal = normalize(record)
    fields = {field.field: field for field in proposal.fields}
    assert fields["risk_frequency"].reported_value == "NR"
    assert fields["risk_frequency"].proposed_value is None
    assert (
        fields["beta_direction"].reported_value
        == fields["beta_direction"].proposed_value
        == "-"
    )
    assert (
        fields["description"].reported_value
        == fields["description"].proposed_value
        == "NR"
    )
    assert any("Uninterpreted beta_direction" in note for note in proposal.unresolved)
    study = extract(root, load_run(root)).records[1]
    study_fields = {field.field: field for field in normalize(study).fields}
    assert study_fields["replication_sample_size"].proposed_value == "NA"
    record.fields["a/b~c"] = "preserved"
    pointer = source_location(record, "a/b~c")
    assert pointer.endswith("/a~1b~0c")
    assert (
        resolve_pointer({"a/b~c": "preserved"}, pointer.replace(record.locator, ""))
        == "preserved"
    )


def test_wrong_ontology_and_unrecognized_executable_fields_are_not_imported(
    tmp_path: Path,
) -> None:
    unrelated, valid = associations()
    unrelated["efo_traits"] = [{"efo_id": "EFO_9999999"}]
    valid["genotype_scores"] = {"AA": 0.9}
    valid["interpretation"] = {"strategy": "allele_count", "counted_allele": "A"}
    valid["or_per_copy_num"] = 1.8
    root = mutated_run(tmp_path, [unrelated, valid])
    dossier = replay(root, tmp_path / "proposal")
    raw = extract(root, load_run(root))
    assert "ontology mismatch" in " ".join(raw.warnings)
    assert sum(record.kind == "association" for record in raw.records) == 1
    fields = {
        field.field: field.proposed_value for field in normalize(raw.records[0]).fields
    }
    assert fields["or_per_copy_num"] == 1.8  # Reported measure only.
    assert "genotype_scores" not in fields and "interpretation" not in fields
    assert dossier.interpretation is None
    assert all(item.result_key is None for item in dossier.explanations)


@pytest.mark.parametrize("study_pmid", [31791255, 99999999, None])
def test_association_study_identity_controls_context_drafting(
    tmp_path: Path, study_pmid: int | None
) -> None:
    root = mutated_run(tmp_path, [associations()[0]])
    run = load_run(root)
    response = next(item for item in run.responses if item.kind == "study")
    assert response.path
    path = root / response.path
    study = json.loads(path.read_bytes())
    if study_pmid is None:
        study.pop("pubmed_id")
    else:
        study["pubmed_id"] = study_pmid
    study["initial_sample_size"] = "123 Fictional recruitment-context participants"
    study["discovery_ancestry"] = ["Fictional recruitment-context ancestry"]
    study["bg_efo_traits"] = [
        {
            "efo_id": "EFO_9999999",
            "efo_trait": "Fictional recruitment-context condition",
        }
    ]
    original = stable_json(study)
    replace_response(root, "study", study)

    proposal = tmp_path / "proposal"
    dossier = replay(root, proposal)
    report = unescape((proposal / "review.md").read_text(encoding="utf-8"))
    claim = dossier.claims[0]
    conflict = study_pmid == 99999999
    study_ref = "e-gwas-study-GCST009418"
    assert (study_ref in claim.evidence_ids) == (not conflict)
    # The exact association-linked PMID remains usable, independently of the study.
    assert "e-europe-pmc-MED-31791255" in claim.evidence_ids
    retained_study = next(e for e in dossier.evidence if e.evidence_id == study_ref)
    assert "Fictional recruitment-context" in retained_study.statement
    background_note = (
        "Source-reported bg_efo_traits (response-004#/bg_efo_traits): "
        + json.dumps(study["bg_efo_traits"])
    )
    assert background_note in retained_study.validation_notes
    assert (background_note in claim.limitations) == (not conflict)
    raw = json.loads((proposal / "raw-extraction.json").read_bytes())
    raw_study = next(r for r in raw["records"] if r["kind"] == "study")
    assert raw_study["fields"].get("pubmed_id") == study_pmid
    assert raw_study["fields"]["initial_sample_size"] == study["initial_sample_size"]
    assert raw_study["fields"]["discovery_ancestry"] == study["discovery_ancestry"]
    assert raw_study["fields"]["bg_efo_traits"] == study["bg_efo_traits"]
    texts = [
        text.body for text in dossier.explanations if claim.claim_id in text.claim_ids
    ]
    assert texts
    assert all(
        ("Fictional recruitment-context" in text) == (not conflict) for text in texts
    )
    inspected = inspect_item(dossier, ReviewScope.CLAIM, claim.claim_id)
    dependency_text = json.dumps(inspected["reviewed"]["dependencies"])
    assert ("Fictional recruitment-context" in dependency_text) == (not conflict)
    if conflict:
        note = next(n for n in claim.limitations if n.startswith("Conflicting"))
        assert (
            "response-003#/_embedded/associations/0/pubmed_id reports 31791255" in note
        )
        assert "response-004#/pubmed_id reports 99999999" in note
        assert note in dossier.evidence[0].validation_notes
        assert note in raw["warnings"]
        assert note in report
        assert all(note in text for text in texts)
    elif study_pmid is None:
        assert any("linked by accession only" in note for note in claim.limitations)
        assert not any("Conflicting" in note for note in claim.limitations)
    assert path.read_bytes() == original
    assert dossier.interpretation is None


def test_wrong_publication_identity_is_withheld(tmp_path: Path) -> None:
    root = mutated_run(tmp_path, associations())
    run = load_run(root)
    response = run.responses[-1]
    assert response.path
    data = json.loads((root / response.path).read_bytes())
    data["resultList"]["result"][0]["pmid"] = "99999999"
    data["resultList"]["result"][0]["id"] = "99999999"
    replace_response(root, "publication", data)
    extraction = extract(root, load_run(root))
    assert "publication identity disagrees" in " ".join(extraction.warnings)
    assert not any(record.kind == "publication" for record in extraction.records)


@pytest.mark.parametrize("failure", ["timeout", "http", "json", "shape", "empty"])
def test_failures_remain_inspectable_without_invented_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    def fetch(url: str) -> tuple[int, bytes]:
        if failure == "timeout":
            raise TimeoutError("Simulated timeout")
        return {
            "http": (429, b'{"error":"rate limited"}'),
            "json": (200, b"not json"),
            "shape": (200, b'{"changed":true}'),
            "empty": (200, b'{"page":{"totalElements":0}}'),
        }[failure]

    monkeypatch.setattr(research_sources, "fetch", fetch)
    root = tmp_path / "run"
    run = acquire(ResearchRequest(trait_name="Unlisted trait"), root)
    dossier = replay(root, root / "proposal")
    assert dossier.evidence == [] and dossier.interpretation is None
    assert run.warnings
    if failure == "http":
        assert run.responses[0].status_code == 429
        assert (
            root / "responses/response-001.json"
        ).read_bytes() == b'{"error":"rate limited"}'
    if failure in {"json", "timeout", "http"}:
        assert run.responses[0].error
    assert "No suitable association" in " ".join(run.warnings)
    report = unescape((root / "proposal/review.md").read_text(encoding="utf-8"))
    assert all(warning in report for warning in run.warnings)
    assert all(response.url in report for response in run.responses)
    assert main(["replay", str(root), str(tmp_path / "empty-replay")]) == 2
    summary = capsys.readouterr().out
    assert "Retrieved sources: 0" in summary and "Evidence proposals: 0" in summary
    assert "no evidence proposals" in summary
    assert "Next: review the report warnings and saved responses." in summary
    assert " init " not in summary
    if failure in {"json", "timeout", "http"}:
        assert "Retrieval failed" in summary


def test_review_handoff_correction_rejection_and_publication_block(
    tmp_path: Path,
) -> None:
    output, workspace = tmp_path / "proposal", tmp_path / "review"
    dossier = replay(FROZEN, output)
    original = (output / "dossier.json").read_bytes()
    assert main(["init", str(output / "dossier.json"), str(workspace)]) == 0
    assert not (workspace / "decisions.jsonl").read_bytes()
    target = dossier.evidence[0].evidence_id
    decide(workspace, ReviewScope.EVIDENCE, target, ReviewAction.REQUEST_CHANGES)
    corrected = get_snapshot(workspace).dossier
    corrected.evidence[0].statement += " Relevance remains unresolved."
    corrected.explanations[0].body = "Reviewer-corrected draft wording."
    revise_workspace(workspace, corrected, "Fictional correction demonstration.")
    decide(workspace, ReviewScope.EVIDENCE, target, ReviewAction.REJECT)
    assert workspace_status(workspace)["items"][0]["state"] == "rejected"
    assert len(workspace_history(workspace)["revisions"]) == 2
    assert (output / "dossier.json").read_bytes() == original
    with pytest.raises(ValueError, match="Stage 3 review is not ready"):
        build_candidate(
            workspace,
            tmp_path / "candidate",
            "blocked",
            EXAMPLES / "synthetic-educational-cases.json",
        )
    assert not (tmp_path / "candidate").exists()


def test_independent_literature_and_unselected_ontology_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original = json.loads((FROZEN / "responses/response-005.json").read_bytes())[
        "resultList"
    ]["result"][0]
    second = {
        **deepcopy(original),
        "id": "9990001",
        "pmid": "9990001",
        "title": "Fictional bibliographic context",
        "abstractText": "Untrusted narrative about genetic effects.",
    }
    bad = {**deepcopy(original), "id": "123", "pmid": "456"}
    queries: list[str] = []

    def fetch(url: str) -> tuple[int, bytes]:
        path = urlsplit(url).path
        params = parse_qs(urlsplit(url).query)
        if path.endswith("efo-traits"):
            data = {
                "_embedded": {
                    "efo_traits": [
                        {
                            "efo_id": "EFO_9999999",
                            "efo_trait": "Different scientific terminology",
                        }
                    ]
                }
            }
        else:
            assert path.endswith("search")  # No associations or exact PMID requests.
            query = params["query"][0]
            queries.append(query)
            assert params["pageSize"] == ["3"]
            data = {
                "resultList": {
                    "result": (
                        [original, original, bad]
                        if len(queries) == 1
                        else [original, second, bad]
                    )
                }
            }
        return 200, stable_json(data)

    monkeypatch.setattr(research_sources, "fetch", fetch)
    root = tmp_path / "independent"
    assert (
        main(
            [
                "research",
                "Digestive example",
                str(root),
                "--synonym",
                "Review term",
                "--limit",
                "3",
            ]
        )
        == 0
    )
    assert queries == [
        'TITLE_ABS:"Digestive example" AND SRC:MED',
        'TITLE_ABS:"Review term" AND SRC:MED',
    ]
    run = load_run(root)
    extraction = extract(root, run)
    assert len(extraction.records) == 2
    assert all(record.kind == "publication" for record in extraction.records)
    assert len(extraction.records[0].found_by) == 3
    assert "Review term" in " ".join(extraction.records[0].found_by)
    assert "identity disagrees" in " ".join(extraction.warnings)
    assert len(extraction.ontology_candidates) == 1
    candidate = extraction.ontology_candidates[0]
    assert len(candidate.found_by) == 2
    assert "not selected automatically" in " ".join(candidate.found_by)
    assert candidate.fields["efo_trait"] == "Different scientific terminology"
    dossier = replay(root, tmp_path / "replay-independent")
    assert all(
        e.claim_type == "other" and e.rsid is None and e.phenotype is None
        for e in dossier.evidence
    )
    assert all(
        c.claim_type == "other" and c.status == "pending" for c in dossier.claims
    )
    assert dossier.interpretation is None
    assert all(
        "Bibliographic candidate only" in text.body for text in dossier.explanations
    )
    assert all(second["abstractText"] not in text.body for text in dossier.explanations)
    report = unescape((root / "proposal/review.md").read_text(encoding="utf-8"))
    assert "Different scientific terminology" in report
    assert "Abstract reading context" in report and "/abstractText" in report
    assert "limited" in " ".join(run.warnings) or "bounded" in " ".join(run.warnings)
    assert "Evidence proposals: 2 | Draft explanations: 2" in capsys.readouterr().out


def test_long_qualifier_does_not_become_a_trait_description(tmp_path: Path) -> None:
    first, second = associations()
    qualifier = "Discovery cohort qualification. " * 80
    assert len(qualifier) > 2400
    first["description"] = qualifier
    root = mutated_run(tmp_path / "long", [first, second])
    original = (root / "responses/response-003.json").read_bytes()
    dossier = replay(root, tmp_path / "long-proposal")
    assert len(dossier.evidence) == 4
    assert dossier.candidate.description is not None
    assert len(dossier.candidate.description) <= 2000
    assert qualifier not in dossier.candidate.description
    assert qualifier in " ".join(dossier.evidence[0].validation_notes)
    assert qualifier in " ".join(dossier.claims[0].limitations)
    assert any(qualifier in text.body for text in dossier.explanations)
    assert (root / "responses/response-003.json").read_bytes() == original
    # An individually invalid phenotype is withheld; its neighbor remains usable.
    first["reported_trait"] = ["Invalid overlong phenotype. " * 100]
    invalid = mutated_run(tmp_path / "invalid", [first, second])
    remaining = replay(invalid, tmp_path / "remaining")
    assert len(remaining.evidence) == 3
    assert any(item.evidence_id.endswith("55467053") for item in remaining.evidence)
    raw = json.loads((tmp_path / "remaining/raw-extraction.json").read_bytes())
    assert any("dossier proposal withheld" in warning for warning in raw["warnings"])
    assert raw["records"][0]["fields"]["description"] == qualifier


@pytest.mark.parametrize("direction", ["-", "increase", "decrease", "unknown"])
def test_structured_direction_requires_a_supported_explicit_label(
    tmp_path: Path, direction: str
) -> None:
    row = associations()[0]
    row["beta_direction"] = direction
    root = mutated_run(tmp_path, [row])
    raw = extract(root, load_run(root)).records[0]
    fields = {item.field: item for item in normalize(raw).fields}
    assert (
        fields["beta_direction"].reported_value
        == fields["beta_direction"].proposed_value
        == direction
    )
    dossier = replay(root, tmp_path / "proposal")
    assert dossier.evidence[0].effect_direction == (
        direction if direction in {"increase", "decrease"} else None
    )
    if direction in {"-", "unknown"}:
        assert any(
            "Structured effect direction withheld" in note
            for note in dossier.evidence[0].validation_notes
        )


def test_drafts_use_linked_study_context_and_explicit_claim_references(
    tmp_path: Path,
) -> None:
    first, second = associations()
    first["snp_allele"][0]["effect_allele"] = "A"
    first["beta_direction"] = "increase"
    root = mutated_run(tmp_path, [first, second])
    dossier = replay(root, tmp_path / "proposal")
    initial = {text.content_id: text.body for text in dossier.explanations}
    association_text = [
        text.body
        for text in dossier.explanations
        if dossier.claims[0].claim_id in text.claim_ids
    ]
    assert any("Reported effect allele: A" in text for text in association_text)
    assert any(
        "Reported effect direction: increase" in text for text in association_text
    )
    assert any("p_value: 1e-06" in text for text in association_text)
    assert all("53 Fulani individuals" in text for text in association_text)
    dossier.claims.reverse()
    dossier.evidence.reverse()
    dossier.explanations = []
    bindings = draft_explanations(dossier)
    assert {text.content_id: text.body for text in dossier.explanations} == initial
    claims = {claim.claim_id: claim for claim in dossier.claims}
    texts = {text.content_id: text for text in dossier.explanations}
    for binding in bindings:
        claim = claims[texts[binding["content_id"]].claim_ids[0]]
        assert set(binding["input_statements"]) == set(claim.evidence_ids)


def test_review_report_renders_external_markdown_as_literal_text(
    tmp_path: Path,
) -> None:
    row = associations()[0]
    row["reported_trait"] = [
        "**Injected** [link](https://invalid.example)\n\n# Hijacked\n\n---"
    ]
    row["description"] = "![image](https://invalid.example/img) <script>bad</script>"
    root = mutated_run(tmp_path, [row])
    replay(root, tmp_path / "proposal")
    report = (tmp_path / "proposal/review.md").read_text(encoding="utf-8")
    rendered = mistune.html(report)
    assert isinstance(rendered, str)
    assert '<a href="https://invalid.example' not in rendered
    assert '<img src="https://invalid.example' not in rendered
    assert (
        "<strong>Injected</strong>" not in rendered
        and "<h1>Hijacked</h1>" not in rendered
    )
    assert "<script>bad</script>" not in rendered
    assert "**Injected**" in unescape(rendered)


@pytest.mark.parametrize("data", [{"_embedded": None}, {"page": []}])
def test_collection_reports_malformed_response_containers(data: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="Unsupported GWAS response"):
        collection(data, "associations")


def test_cli_search_replay_and_helpful_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recorded_network(monkeypatch)
    root = tmp_path / "run"
    assert (
        main(["research", "Lactose Digestion Ability", str(root), "--limit", "2"]) == 0
    )
    output = capsys.readouterr().out
    assert "research" not in output.split("Next:")[-1]
    assert " init " in output and "Evidence proposals: 4" in output
    assert "Trait: Lactose Digestion Ability" in output
    assert "Retrieved sources: 4" in output and "Draft explanations: 14" in output
    assert "Warning: 2 finding(s) have unresolved markers or alleles." in output
    assert "Warnings recorded:" in output and "Search results are bounded." in output
    assert "Next: Review proposed information" in output
    assert "Report: " + str(root / "proposal/review.md") in output
    assert "Proposal data: " + str(root / "proposal") in output
    assert "Saved sources: " + str(root) in output
    assert "GWAS Catalog lists" not in output and "response-003" not in output
    assert len(output.splitlines()) <= 12
    assert main(["replay", str(root), str(tmp_path / "replay")]) == 0
    replayed = capsys.readouterr().out
    assert "Evidence proposals: 4 | Draft explanations: 14" in replayed
    assert "Report: " + str(tmp_path / "replay/review.md") in replayed
    assert "Saved sources: " + str(root) in replayed
    assert len(replayed.splitlines()) <= 12
    workspace = tmp_path / "review"
    assert main(["init", str(root / "proposal/dossier.json"), str(workspace)]) == 0
    capsys.readouterr()
    assert main(["status", str(workspace)]) == 0
    status = capsys.readouterr().out
    assert "Ready to publish: no" in status and "Ready for Stage 4" not in status
    assert main(["status", str(workspace), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ready_for_stage4"] is False
    with pytest.raises(SystemExit) as error:
        main(["research", "Trait", str(tmp_path / "bad"), "--limit", "0"])
    assert error.value.code == 2
    assert "Traceback" not in capsys.readouterr().err
    assert not (tmp_path / "bad").exists()
