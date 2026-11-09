"""Offline release acceptance tests. Every recorded approval is fictional.

Sections follow compilation, preview, interpretation and publication. Shared
end-to-end fixtures stay here; Stage 2 owns the individual rule model contracts.
"""

import json
import shutil
from collections.abc import Callable
from html import escape, unescape
from pathlib import Path
from typing import cast

import mistune
import pytest
from pydantic import ValidationError

from backend.models.curation import ReviewAction, TraitDossier
from backend.models.interpretation import AlleleCountInterpretation
from backend.models.published_catalog import PublishedTrait, TraitCatalog
from backend.services.trait_curation import compiler
from backend.services.trait_curation.cli import main
from backend.services.trait_curation.compiler import (
    approve_release,
    build_candidate,
    compile_catalog,
    preview_candidate,
    publish_candidate,
    sha256,
    source_documents,
    stable_json,
    verify_release,
)
from backend.services.trait_curation.offline import Observation, evaluate
from backend.services.trait_curation.preview import (
    _format_metadata,
    _plain_text,
    render_preview,
)
from backend.services.trait_curation.verification import ExpectedCases, verify_cases
from backend.services.trait_curation.workflow import (
    ReviewScope,
    get_snapshot,
    initialize_workspace,
    inspect_item,
    load_dossier,
    read_workspace,
    record_decision,
    review_targets,
    revise_workspace,
)

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "curation/examples"
CASES = EXAMPLES / "synthetic-stage4-cases.json"


@pytest.fixture(scope="module")
def markdown_renderer() -> Callable[[str], str]:
    return cast(Callable[[str], str], mistune.html)


def test_saved_fictional_release_is_intact() -> None:
    # Deliberately retained artifact: verification also exercises today's evaluator
    # and renderer. Do not regenerate it to hide a compatibility regression.
    release = ROOT / "data/releases/synthetic-stage4-demo-v1"
    manifest = verify_release(release)
    assert manifest.trait_id == "synthetic_allele"
    inputs = json.loads((release / "inputs.json").read_bytes())
    assert inputs["expected_cases"]["kind"] == "synthetic"
    assert all(item["reviewer_id"] == "synthetic-demo" for item in inputs["decisions"])


@pytest.fixture
def dossier() -> TraitDossier:
    return load_dossier(EXAMPLES / "synthetic-stage4-dossier.json")


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
        "synthetic-reviewer",
        "Fictional software test; no scientific approval.",
        inspected["revision"],
        inspected["fingerprint"],
    )


def approve_all(workspace: Path) -> None:
    for scope, target in review_targets(get_snapshot(workspace).dossier):
        decide(workspace, scope, target)


@pytest.fixture
def workspace(dossier: TraitDossier, tmp_path: Path) -> Path:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Fictional publication demonstration.")
    approve_all(workspace)
    return workspace


@pytest.fixture
def candidate(workspace: Path, tmp_path: Path) -> Path:
    path = tmp_path / "candidate"
    build_candidate(workspace, path, "synthetic-r1", CASES)
    return path


def approve(candidate: Path, workspace: Path) -> None:
    approve_release(
        candidate,
        workspace,
        "synthetic-release-reviewer",
        "Fictional publication test only.",
        sha256((candidate / "manifest.json").read_bytes()),
    )


def catalog(candidate: Path) -> TraitCatalog:
    return TraitCatalog.model_validate_json((candidate / "catalog.json").read_bytes())


def files_under(path: Path) -> dict[str, bytes]:
    return {
        str(file.relative_to(path)): file.read_bytes()
        for file in path.rglob("*")
        if file.is_file()
    }


def rehash_candidate(candidate: Path) -> None:
    """Let tampering tests reach semantic checks beyond ordinary file integrity."""
    manifest = json.loads((candidate / "manifest.json").read_bytes())
    for name in manifest["files"]:
        manifest["files"][name] = sha256((candidate / name).read_bytes())
    (candidate / "manifest.json").write_bytes(stable_json(manifest))


# Compilation, review eligibility and the published schema.


def test_compact_catalog_uses_decisions_and_excludes_workflow_data(
    dossier: TraitDossier,
    tmp_path: Path,
) -> None:
    dossier.candidate.reviewer_notes = ["PRIVATE REVIEW NOTES"]
    dossier.evidence[0].validation_notes = ["INTERNAL EXTRACTION DISCUSSION"]
    unused = dossier.evidence[0].model_copy(deep=True)
    unused.evidence_id = "unused-finding"
    unused.statement = "UNUSED RESEARCH"
    dossier.evidence.append(unused)
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Fictional research.")
    decide(
        workspace, ReviewScope.MODEL, dossier.candidate.proposed_id, ReviewAction.REJECT
    )
    approve_all(workspace)
    snapshots, decisions = read_workspace(workspace)
    result = compile_catalog(snapshots[-1].dossier, decisions)
    data = result.model_dump_json()
    assert result.schema_version == "3.1"
    assert isinstance(result.traits[0], PublishedTrait)
    for value in (
        "PRIVATE REVIEW NOTES",
        "INTERNAL EXTRACTION DISCUSSION",
        "UNUSED RESEARCH",
        '"candidate"',
        '"status"',
        '"reviewed"',
        '"assessment"',
        '"extraction_method"',
        '"reviewer_id"',
        '"score"',
        '"confidence"',
    ):
        assert value not in data
    assert result.traits[0].claims[0].limitations == dossier.claims[0].limitations
    assert (
        result.traits[0].evidence[0].source_location
        == dossier.evidence[0].source_location
    )
    assert snapshots[-1].dossier.candidate.status == "draft"
    assert snapshots[-1].dossier.claims[0].status == "pending"
    assert TraitCatalog.model_validate_json(data) == result


@pytest.mark.parametrize(
    "state,review_state",
    [
        ("missing", "pending"),
        ("partial", "pending"),
        ("rejected", "rejected"),
        ("blocked", "blocked"),
        ("stale", "stale"),
    ],
)
def test_ineffective_reviews_block_compilation(
    dossier: TraitDossier,
    tmp_path: Path,
    state: str,
    review_state: str,
) -> None:
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Fictional draft.")
    if state == "partial":
        decide(workspace, ReviewScope.EVIDENCE, dossier.evidence[0].evidence_id)
    elif state != "missing":
        approve_all(workspace)
        if state == "rejected":
            decide(
                workspace,
                ReviewScope.MODEL,
                dossier.candidate.proposed_id,
                ReviewAction.REJECT,
            )
        elif state == "blocked":
            decide(
                workspace,
                ReviewScope.EVIDENCE,
                dossier.evidence[0].evidence_id,
                ReviewAction.REQUEST_CHANGES,
            )
        else:
            dossier.evidence[0].statement = "Corrected fictional finding."
            revise_workspace(workspace, dossier, "Correct evidence.")
    with pytest.raises(
        ValueError, match=f"Stage 3 review is not ready: .* is {review_state}"
    ):
        build_candidate(workspace, tmp_path / "candidate", "example", CASES)
    assert not (tmp_path / "candidate").exists()


def test_approved_labels_never_authorize_build(tmp_path: Path) -> None:
    data = json.loads((EXAMPLES / "synthetic-reviewed-catalog.json").read_bytes())
    workspace = tmp_path / "review"
    initialize_workspace(
        workspace, TraitDossier.model_validate(data["traits"][0]), "Labels only."
    )
    with pytest.raises(ValueError, match="Stage 3 review is not ready"):
        build_candidate(workspace, tmp_path / "candidate", "example", CASES)


@pytest.mark.parametrize(
    "change,message",
    [
        ("missing_rule", "publication requires a complete genotype table"),
        ("missing_content", "publication requires outcome_summary"),
        ("missing_general", "publication requires a general explanation"),
        ("missing_category", "category"),
        ("missing_description", "description"),
    ],
)
def test_reviewed_but_incomplete_publication_is_rejected(
    dossier: TraitDossier,
    tmp_path: Path,
    change: str,
    message: str,
) -> None:
    if change == "missing_rule":
        assert isinstance(dossier.interpretation, AlleleCountInterpretation)
        dossier.interpretation.rules.pop()
        dossier.explanations = [
            item for item in dossier.explanations if item.result_key != "2"
        ]
    elif change == "missing_content":
        dossier.explanations.pop()
    elif change == "missing_general":
        dossier.explanations.pop(0)
    elif change == "missing_category":
        dossier.candidate.proposed_category = None
    else:
        dossier.candidate.description = None
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Incomplete fictional draft.")
    approve_all(workspace)
    with pytest.raises(ValidationError, match=message):
        build_candidate(workspace, tmp_path / "candidate", "example", CASES)


def test_compiler_revalidates_mutated_models_before_reviews(
    dossier: TraitDossier,
) -> None:
    assert isinstance(dossier.interpretation, AlleleCountInterpretation)
    dossier.interpretation.rules[0].copies = 2
    # No decisions: a review error cannot satisfy this structural assertion.
    with pytest.raises(ValidationError, match="copies must match the counted allele"):
        compile_catalog(dossier, [])


@pytest.mark.parametrize(
    "mutation,message",
    [
        ("extra_score", "Extra inputs are not permitted"),
        ("missing_reference", "claim evidence reference missing IDs"),
        ("old_schema", "Input should be '3.1'"),
        ("authoring_payload", "traits.0.candidate"),
        ("unsupported_content", "result_key must match an allele count or unavailable"),
    ],
)
def test_published_schema_rejects_invalid_or_old_contracts(
    candidate: Path, mutation: str, message: str
) -> None:
    data = json.loads((candidate / "catalog.json").read_bytes())
    if mutation == "extra_score":
        data["traits"][0]["interpretation"]["rules"][0]["score"] = 0.5
    elif mutation == "missing_reference":
        data["traits"][0]["claims"][0]["evidence_ids"] = ["missing"]
    elif mutation == "old_schema":
        data["schema_version"] = "3.0"
    elif mutation == "unsupported_content":
        data["traits"][0]["explanations"][-1]["result_key"] = "likely"
    else:
        data["traits"][0] = load_dossier(
            EXAMPLES / "synthetic-stage4-dossier.json"
        ).model_dump()
    with pytest.raises(ValidationError, match=message):
        TraitCatalog.model_validate(data)


@pytest.mark.parametrize(
    "release_id",
    ["", "../other-release", "release/name", "release\\name", "release name", "r" * 81],
    ids=["empty", "parent", "slash", "backslash", "space", "over-80-characters"],
)
def test_invalid_release_ids_leave_no_candidate(
    workspace: Path, tmp_path: Path, release_id: str
) -> None:
    candidate = tmp_path / "candidate"
    with pytest.raises(ValidationError) as error:
        build_candidate(workspace, candidate, release_id, CASES)
    assert [item["type"] for item in error.value.errors()] == [
        "string_pattern_mismatch"
    ]
    assert not candidate.exists()


def test_repeat_builds_ignore_output_path_clock_and_randomness(
    workspace: Path,
    candidate: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copied = tmp_path / "unrelated" / "renamed-workspace"
    shutil.copytree(workspace, copied)

    class NoClock:
        @staticmethod
        def now(*args: object) -> None:
            raise AssertionError("Build must not consult the clock")

    monkeypatch.setattr(compiler, "datetime", NoClock)
    second = tmp_path / "different-output"
    build_candidate(copied, second, "synthetic-r1", CASES)
    assert files_under(candidate) == files_under(second)
    with pytest.raises(FileExistsError):
        build_candidate(copied, second, "synthetic-r1", CASES)


# Preview visibility, literal text and byte preservation.


def test_independent_cases_and_preview_cover_compiled_content(candidate: Path) -> None:
    compiled = catalog(candidate)
    cases = ExpectedCases.model_validate_json(CASES.read_bytes())
    report = verify_cases(compiled.traits[0], cases)
    assert report["passed"]
    assert report["cases"][-1]["state"] == "deferred"
    preview, fingerprint = preview_candidate(candidate)
    assert fingerprint == sha256((candidate / "manifest.json").read_bytes())
    trait = compiled.traits[0]
    for text in (
        trait.name,
        trait.description,
        trait.category,
        trait.claims[0].statement,
        trait.claims[0].scope,
        *trait.claims[0].limitations,
        *[item.body for item in trait.explanations],
    ):
        assert text in preview
    assert (
        "| GG | 0 |" in preview and "| AG | 1 |" in preview and "| AA | 2 |" in preview
    )
    assert (
        "deferred" in preview and "forward_genomic" in preview and "withhold" in preview
    )
    assert "- source_type: other\n" in preview
    assert '- source_location: {"section": "Fictional results"}\n' in preview
    assert (
        render_preview(compiled, report).encode("utf-8")
        == (candidate / "preview.md").read_bytes()
    )


@pytest.mark.parametrize(
    "text",
    [
        "2. Two copies observed",
        "- Evidence is limited",
        "# Genetic interpretation\n**Evidence** and `A\\G`\n"
        "```text\n[A](https://example.org) | ~~B~~\n```",
        "A < B & β > α; <sup>Łódź – 日本語</sup>; literal &amp; and &#x31;",
        "    Indented text\n\tSecond line\nThird line",
    ],
    ids=["numbered", "bulleted", "markdown", "html-unicode-entities", "indented"],
)
def test_scientific_prose_renders_as_literal_text(
    text: str, markdown_renderer: Callable[[str], str]
) -> None:
    # A single paragraph containing the original characters: no scientific
    # text becomes a heading, list, emphasis, link, HTML element or code block.
    assert markdown_renderer(_plain_text(text)) == f"<p>{escape(text)}</p>\n"


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_prose_line_endings_cannot_create_markdown_blocks(
    newline: str, markdown_renderer: Callable[[str], str]
) -> None:
    lines = ["Heading-like text", "===", "---", "+ Item", "2) Item", "    Indentation"]
    expected = escape("\n".join(lines))
    assert markdown_renderer(_plain_text(newline.join(lines))) == f"<p>{expected}</p>\n"


def test_source_and_evidence_metadata_render_literally(
    candidate: Path, markdown_renderer: Callable[[str], str]
) -> None:
    data = catalog(candidate).model_dump(mode="json")
    metadata = {
        "gene": "CYP2D6*1/*4",
        "phenotype": "<sup>Phenotype</sup> &amp;",
        "effect_allele": "A\\*",
        "effect_direction": "[higher](https://example.org)",
    }
    data["traits"][0]["evidence"][0].update(metadata)
    title = "Łódź – β activity in 日本語"
    data["traits"][0]["sources"][0].update(title=title, publication_year=2024)
    compiled = TraitCatalog.model_validate(data)
    report = json.loads((candidate / "verification.json").read_bytes())

    rendered = markdown_renderer(render_preview(compiled, report))

    for key, value in metadata.items():
        expected = escape(json.dumps(value, ensure_ascii=False))
        assert f"<li>{key}: {expected}</li>" in rendered
    assert f"<li>title: {title}</li>" in rendered
    assert "<li>publication_year: 2024</li>" in rendered


def test_preview_identifiers_render_literally(
    candidate: Path, markdown_renderer: Callable[[str], str]
) -> None:
    label = "*label* <i>x</i> &amp; [link](https://example.org)"
    source_id, evidence_id, claim_id, content_id, case_set_id = (
        f"{kind}-{label}"
        for kind in ("source", "evidence", "claim", "content", "cases")
    )
    data = catalog(candidate).model_dump(mode="json")
    trait_data = data["traits"][0]
    trait_data["sources"][0]["source_id"] = source_id
    trait_data["evidence"][0].update(evidence_id=evidence_id, source_ids=[source_id])
    trait_data["claims"][0].update(claim_id=claim_id, evidence_ids=[evidence_id])
    trait_data["interpretation"]["claim_ids"] = [claim_id]
    trait_data["explanations"][0]["content_id"] = content_id
    for content in trait_data["explanations"]:
        content["claim_ids"] = [claim_id]
    compiled = TraitCatalog.model_validate(data)
    cases_data = json.loads(CASES.read_bytes())
    cases_data["case_set_id"] = case_set_id
    for case in cases_data["cases"]:
        case["case_id"] += label
    cases = ExpectedCases.model_validate(cases_data)
    report = verify_cases(compiled.traits[0], cases)
    assert report["passed"]

    rendered = markdown_renderer(render_preview(compiled, report))

    assert f"<h3>{escape(claim_id)}</h3>" in rendered
    assert f"<h3>{escape(source_id)}:" in rendered
    assert f"<strong>{escape(evidence_id)}</strong>:" in rendered
    assert f"Evidence: {escape(evidence_id)}" in rendered
    assert f"Supporting claims: {escape(claim_id)}" in rendered
    assert f"<h3>{escape(content_id)} (simple_explanation; general)</h3>" in rendered
    assert f"Claims: {escape(claim_id)}" in rendered
    assert f"Case set: {escape(case_set_id)} (synthetic)" in rendered
    for result in report["cases"]:
        assert f"<strong>{escape(result['case_id'])}</strong>:" in rendered
        if "actual" in result:
            expected_ids = escape(", ".join(result["content_ids"]))
            assert f"Explanation IDs: {expected_ids}." in rendered


@pytest.mark.parametrize("genotype", ["``<em>AA</em>``", "`x``y```"])
def test_verification_input_backticks_stay_inside_code(
    candidate: Path, genotype: str, markdown_renderer: Callable[[str], str]
) -> None:
    compiled = catalog(candidate)
    data = json.loads(CASES.read_bytes())
    malformed = next(
        case for case in data["cases"] if case["case_id"] == "P3-malformed"
    )
    malformed["observation"]["genotype"] = genotype
    cases = ExpectedCases.model_validate(data)
    report = verify_cases(compiled.traits[0], cases)
    assert report["passed"]

    rendered = markdown_renderer(render_preview(compiled, report))

    expected = escape(json.dumps(malformed["observation"], sort_keys=True))
    assert f"Input: <code>{expected}</code>." in rendered


def test_source_metadata_structures_use_unicode_json(
    markdown_renderer: Callable[[str], str],
) -> None:
    # Sources currently have scalar fields; test nested formatting without
    # inventing fields in the scientific schema.
    value = {
        "cohorts": [
            {"name": "Łódź", "note": "# **α** `β` <γ> &amp;", "included": True},
            {"locations": ["日本語", "- Zürich\n2. [A]"], "missing": None},
        ]
    }
    formatted = _format_metadata(value)
    assert markdown_renderer(formatted) == (
        f"<p>{escape(json.dumps(value, ensure_ascii=False))}</p>\n"
    )
    assert json.loads(unescape(formatted)) == value
    assert "Łódź" in formatted
    assert "\\u" not in formatted


def test_plain_scientific_text_preserves_preview_structure_and_integrity(
    dossier: TraitDossier,
    tmp_path: Path,
    markdown_renderer: Callable[[str], str],
) -> None:
    prose = (
        "2. Two copies observed\n"
        "- Evidence is limited\n"
        "# Genetic interpretation\n"
        "**Strong evidence** and `A\\G`\n"
        "A < B & β > α\n"
        "    Indented observation\n"
        "\tIndented observation"
    )
    location = "# Results *label* `A` <B> β"
    dossier.claims[0].statement = prose
    dossier.explanations[0].body = prose
    dossier.explanations[0].title = "Context [A/G]"
    dossier.evidence[0].statement = "p < 0.05 & β > α"
    dossier.evidence[0].source_location.section = location
    dossier.sources[0].title = "Study *label*"
    workspace = tmp_path / "review"
    initialize_workspace(workspace, dossier, "Fictional Markdown rendering test.")
    approve_all(workspace)
    candidate = tmp_path / "candidate"
    build_candidate(workspace, candidate, "markdown-r1", CASES)
    original = files_under(candidate)

    preview, fingerprint = preview_candidate(candidate)

    rendered = markdown_renderer(preview)
    assert rendered.count(f"<p>{escape(prose)}</p>") == 2
    assert "<h3>synthetic-reviewed-claim</h3>" in rendered
    assert "<p>Context [A/G]</p>" in rendered
    assert "<strong>synthetic-finding</strong>: p &lt; 0.05 &amp; β &gt; α" in rendered
    assert "<li>title: Study *label*</li>" in rendered
    location_json = json.dumps({"section": location}, ensure_ascii=False)
    assert f"<li>source_location: {escape(location_json)}</li>" in rendered
    assert fingerprint == sha256(original["manifest.json"])
    compiled = catalog(candidate)
    assert compiled.traits[0].claims[0].statement == prose
    assert compiled.traits[0].explanations[0].body == prose
    report = json.loads(original["verification.json"])
    catalog_before = stable_json(compiled.model_dump(mode="json"))
    report_before = stable_json(report)
    assert render_preview(compiled, report).encode("utf-8") == original["preview.md"]
    assert stable_json(compiled.model_dump(mode="json")) == catalog_before
    assert stable_json(report) == report_before
    assert files_under(candidate) == original

    approve(candidate, workspace)
    release = publish_candidate(candidate, workspace, tmp_path / "releases")
    assert verify_release(release).release_id == "markdown-r1"
    assert (release / "preview.md").read_bytes() == original["preview.md"]


# Offline interpretation and independently authored cases.


@pytest.mark.parametrize("genotype,count", [("GG", 0), ("AG", 1), ("GA", 1), ("aa", 2)])
def test_allele_count_results(candidate: Path, genotype: str, count: int) -> None:
    raw = json.loads(CASES.read_bytes())["cases"][0]["observation"]
    result = evaluate(
        catalog(candidate).traits[0],
        Observation.model_validate({**raw, "genotype": genotype}),
    )
    assert (
        result.status == "evaluated"
        and result.copies == count
        and result.reason is None
    )
    assert {item.result_key for item in result.explanations} == {None, str(count)}


@pytest.mark.parametrize(
    "field,value",
    [
        ("rsid", "rs1"),
        ("chromosome", "2"),
        ("position", 999),
        ("sequence_accession", "NC_000001.10"),
        ("ploidy", 1),
        ("coordinate_system", "0-based"),
        ("orientation", "reverse_genomic"),
        ("genome_build", "unknown"),
        ("genotype", "ACGT"),
        ("genotype", "GC"),
    ],
)
def test_incompatible_observations_withhold(
    candidate: Path, field: str, value: object
) -> None:
    raw = json.loads(CASES.read_bytes())["cases"][0]["observation"]
    result = evaluate(
        catalog(candidate).traits[0], Observation.model_validate({**raw, field: value})
    )
    assert result.status == "unavailable" and result.copies is None
    assert {item.result_key for item in result.explanations} == {None, "unavailable"}


def test_every_representation_field_is_required(candidate: Path) -> None:
    raw = json.loads(CASES.read_bytes())["cases"][0]["observation"]
    for field in set(raw) - {"genotype"}:
        observation = Observation.model_validate({**raw, field: None})
        result = evaluate(catalog(candidate).traits[0], observation)
        assert result.reason == "missing_representation" and result.copies is None


def test_educational_release_never_produces_genotype_results(tmp_path: Path) -> None:
    data = json.loads((EXAMPLES / "synthetic-reviewed-catalog.json").read_bytes())[
        "traits"
    ][0]
    data["candidate"].update(
        proposed_category="nutrition", description="Fictional education only."
    )
    workspace = tmp_path / "review"
    initialize_workspace(
        workspace, TraitDossier.model_validate(data), "Fictional education."
    )
    approve_all(workspace)
    candidate = tmp_path / "candidate"
    build_candidate(
        workspace,
        candidate,
        "education-r1",
        EXAMPLES / "synthetic-educational-cases.json",
    )
    trait = catalog(candidate).traits[0]
    first = evaluate(trait, None)
    assert first == evaluate(trait, Observation(genotype="AA"))
    assert first.status == "educational" and first.copies is None
    assert first.explanations == trait.explanations
    approve(candidate, workspace)
    verify_release(publish_candidate(candidate, workspace, tmp_path / "releases"))


def test_rs671_reference_cases_without_creating_scientific_approvals(
    candidate: Path,
    tmp_path: Path,
) -> None:
    real_path = ROOT / "curation/alcohol_flush/stage2-draft.json"
    before = real_path.read_bytes()
    real = load_dossier(real_path)
    # Exercise the recorded placements and arithmetic with fictional claim text.
    # This is a schema-level test object, not a compiled or approved real release.
    data = catalog(candidate).traits[0].model_dump(mode="json")
    assert real.interpretation is not None
    data["id"] = "alcohol_flush"
    data["interpretation"] = real.interpretation.model_dump(mode="json")
    data["interpretation"]["claim_ids"] = [data["claims"][0]["claim_id"]]
    trait = PublishedTrait.model_validate(data)
    cases = ExpectedCases.model_validate_json(
        (ROOT / "curation/alcohol_flush/stage4-expected-cases.json").read_bytes()
    )
    assert verify_cases(trait, cases)["passed"]
    real_workspace = tmp_path / "real-unapproved"
    initialize_workspace(real_workspace, real, "Inspect only; no scientific approvals.")
    with pytest.raises(ValueError, match="Stage 3 review is not ready"):
        build_candidate(
            real_workspace,
            tmp_path / "real-candidate",
            "real-r1",
            ROOT / "curation/alcohol_flush/stage4-expected-cases.json",
        )
    assert read_workspace(real_workspace)[1] == [] and real_path.read_bytes() == before


@pytest.mark.parametrize(
    "change,message",
    [
        ("wrong_answer", "Independent cases failed: S1-GRCh38"),
        ("missing_case", "Independent cases missing GRCh38 GG"),
        ("all_deferred", "at least one required independent case is needed"),
    ],
)
def test_failed_or_inadequate_independent_cases_block_build(
    workspace: Path,
    tmp_path: Path,
    change: str,
    message: str,
) -> None:
    data = json.loads(CASES.read_bytes())
    if change == "wrong_answer":
        data["cases"][0]["expected"]["copies"] = 2
    elif change == "missing_case":
        data["cases"].pop(0)
    else:
        data["cases"] = [data["cases"][-1]]
    path = tmp_path / "wrong-cases.json"
    path.write_bytes(stable_json(data))
    with pytest.raises(ValueError, match=message):
        build_candidate(workspace, tmp_path / "candidate", "bad-r1", path)
    assert not (tmp_path / "candidate").exists()


# Frozen inputs, final approval and exact-byte publication.


def test_changed_expectations_cannot_fake_success_with_a_boolean(
    candidate: Path,
    workspace: Path,
    tmp_path: Path,
) -> None:
    inputs = json.loads((candidate / "inputs.json").read_bytes())
    inputs["expected_cases"]["cases"][0]["expected"]["copies"] = 2
    (candidate / "inputs.json").write_bytes(stable_json(inputs))
    rehash_candidate(candidate)
    with pytest.raises(ValueError, match="Independent cases failed"):
        approve(candidate, workspace)
    assert not (candidate / "approval.json").exists()
    # Even a manually forged approval cannot bypass rerunning failed checks.
    (candidate / "approval.json").write_bytes(stable_json({"release_approved": True}))
    with pytest.raises(ValueError, match="Independent cases failed"):
        publish_candidate(candidate, workspace, tmp_path / "releases")


@pytest.mark.parametrize("change", ["decision_fingerprint", "scientific_record"])
def test_frozen_reviews_must_match_snapshots_after_rehashing(
    candidate: Path, workspace: Path, change: str
) -> None:
    history = files_under(workspace)
    inputs = json.loads((candidate / "inputs.json").read_bytes())
    if change == "decision_fingerprint":
        inputs["decisions"][0]["fingerprint"] = "0" * 64
    else:
        dossier = inputs["snapshots"][-1]["dossier"]
        dossier["evidence"][0]["statement"] = "Altered fictional scientific finding."
        # Keep the dossier checksum consistent too, so only the recorded reviews
        # can establish that this otherwise valid scientific record was changed.
        manifest = json.loads((candidate / "manifest.json").read_bytes())
        manifest["dossier_sha256"] = sha256(stable_json(dossier))
        (candidate / "manifest.json").write_bytes(stable_json(manifest))
    (candidate / "inputs.json").write_bytes(stable_json(inputs))
    rehash_candidate(candidate)

    with pytest.raises(
        ValueError, match="^Frozen decision does not match its reviewed snapshot$"
    ):
        approve(candidate, workspace)
    assert not (candidate / "approval.json").exists()
    assert files_under(workspace) == history


def test_approval_is_required_and_bound_to_manifest(
    candidate: Path,
    workspace: Path,
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="approval.json"):
        publish_candidate(candidate, workspace, tmp_path / "releases")
    with pytest.raises(ValueError, match="fingerprint changed"):
        approve_release(
            candidate, workspace, "reviewer", "Fictional rationale.", "0" * 64
        )
    approve(candidate, workspace)
    with pytest.raises(FileExistsError):
        approve(candidate, workspace)
    manifest = candidate / "manifest.json"
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="exact manifest"):
        publish_candidate(candidate, workspace, tmp_path / "releases")


def test_boolean_is_not_a_release_approval(
    candidate: Path, workspace: Path, tmp_path: Path
) -> None:
    (candidate / "approval.json").write_text(
        '{"release_approved":true}', encoding="utf-8"
    )
    with pytest.raises(ValidationError, match="manifest_sha256"):
        publish_candidate(candidate, workspace, tmp_path / "releases")


def test_candidate_preview_must_match_catalog(
    candidate: Path,
    workspace: Path,
) -> None:
    # Rehashing a misleading preview does not make it a valid compiler preview.
    preview = candidate / "preview.md"
    preview.write_text("An invented prediction.", encoding="utf-8")
    rehash_candidate(candidate)
    with pytest.raises(ValueError, match="Preview does not match"):
        approve(candidate, workspace)


@pytest.mark.parametrize("field", ["description", "claim", "explanation"])
def test_catalog_must_match_frozen_dossier_even_after_consistent_edits(
    candidate: Path,
    workspace: Path,
    field: str,
) -> None:
    original = files_under(candidate)
    history = files_under(workspace)
    assert preview_candidate(candidate)[0] == original["preview.md"].decode("utf-8")
    assert files_under(candidate) == original

    changed = catalog(candidate)
    trait = changed.traits[0]
    if field == "description":
        trait.description = "Unreviewed fictional description."
    elif field == "claim":
        trait.claims[0].statement = "Unreviewed fictional claim."
    else:
        trait.explanations[1].body = "Unreviewed fictional result explanation."
    (candidate / "catalog.json").write_bytes(
        stable_json(changed.model_dump(mode="json"))
    )
    verification = json.loads(original["verification.json"])
    (candidate / "preview.md").write_bytes(
        render_preview(changed, verification).encode("utf-8")
    )
    rehash_candidate(candidate)

    edited = files_under(candidate)
    with pytest.raises(
        ValueError, match="Catalog does not match the frozen reviewed dossier"
    ):
        preview_candidate(candidate)
    with pytest.raises(
        ValueError, match="Catalog does not match the frozen reviewed dossier"
    ):
        approve(candidate, workspace)
    assert files_under(candidate) == edited
    assert files_under(workspace) == history
    assert not (candidate / "approval.json").exists()


def test_publish_and_verify_preserve_approved_bytes_without_compiling(
    candidate: Path,
    workspace: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history = files_under(workspace)
    approve(candidate, workspace)
    approved = files_under(candidate)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Publication and verification must not compile")

    monkeypatch.setattr(compiler, "build_candidate", forbidden)
    monkeypatch.setattr(compiler, "compile_catalog", forbidden)
    release = publish_candidate(candidate, workspace, tmp_path / "releases")
    assert all((release / name).read_bytes() == data for name, data in approved.items())
    assert files_under(workspace) == history
    assert files_under(candidate) == approved
    published = files_under(release)
    assert verify_release(release).release_id == "synthetic-r1"
    assert files_under(release) == published
    with pytest.raises(FileExistsError):
        publish_candidate(candidate, workspace, tmp_path / "releases")
    assert files_under(release) == published


@pytest.mark.parametrize(
    "name,error",
    [
        ("catalog.json", "Integrity check failed: catalog.json"),
        ("manifest.json", "exact manifest"),
    ],
)
def test_modifying_approved_files_blocks_publication(
    candidate: Path,
    workspace: Path,
    tmp_path: Path,
    name: str,
    error: str,
) -> None:
    approve(candidate, workspace)
    path = candidate / name
    path.write_bytes(path.read_bytes() + b" ")
    releases = tmp_path / "releases"
    with pytest.raises(ValueError, match=error):
        publish_candidate(candidate, workspace, releases)
    assert not releases.exists()


@pytest.mark.parametrize(
    "name",
    [
        "catalog.json",
        "manifest.json",
        "inputs.json",
        "preview.md",
        "verification.json",
        "approval.json",
        "checksums.json",
    ],
)
def test_modification_of_any_published_file_is_detected(
    candidate: Path,
    workspace: Path,
    tmp_path: Path,
    name: str,
) -> None:
    approve(candidate, workspace)
    release = publish_candidate(candidate, workspace, tmp_path / "releases")
    path = release / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="integrity check failed"):
        verify_release(release)


@pytest.mark.parametrize(
    "change,message",
    [
        ("revision", "Review selection changed"),
        ("rejection", "Stage 3 review is not ready: .* is rejected"),
        ("reapproval", "Required review decisions changed"),
    ],
)
def test_changed_selection_blocks_approval_and_publication(
    candidate: Path,
    workspace: Path,
    tmp_path: Path,
    change: str,
    message: str,
) -> None:
    approve(candidate, workspace)
    published = publish_candidate(candidate, workspace, tmp_path / "previous-release")
    if change == "revision":
        corrected = get_snapshot(workspace).dossier
        corrected.explanations[0].body = "Corrected fictional wording."
        revise_workspace(workspace, corrected, "Correct wording.")
        approve_all(workspace)
    else:
        decide(
            workspace,
            ReviewScope.MODEL,
            "synthetic_allele",
            ReviewAction.REJECT if change == "rejection" else ReviewAction.APPROVE,
        )
    with pytest.raises(ValueError, match=message):
        publish_candidate(candidate, workspace, tmp_path / "new-releases")
    with pytest.raises(ValueError, match=message):
        approve(candidate, workspace)
    # An already published release remains independently verifiable history.
    assert verify_release(published).release_id == "synthetic-r1"


def test_prior_revision_approvals_are_frozen_with_their_snapshots(
    workspace: Path,
    tmp_path: Path,
) -> None:
    dossier = get_snapshot(workspace).dossier
    dossier.candidate.reviewer_notes.append("Workflow note only.")
    revise_workspace(workspace, dossier, "No reviewed payload changed.")
    candidate = tmp_path / "candidate"
    build_candidate(workspace, candidate, "synthetic-r2", CASES)
    inputs = json.loads((candidate / "inputs.json").read_bytes())
    assert len(inputs["snapshots"]) == 2
    assert {item["candidate_revision"] for item in inputs["decisions"]} == {1}
    approve(candidate, workspace)
    verify_release(publish_candidate(candidate, workspace, tmp_path / "releases"))


def test_source_acquisition_provenance_is_preserved(
    workspace: Path, tmp_path: Path
) -> None:
    inventory = tmp_path / "acquisition.json"
    row = {
        "source_id": "synthetic-study",
        "document_id": "fictional-document",
        "sha256": "a" * 64,
        "type": "excerpt",
        "url": "https://example.org/fictional",
        "version": "fictional-v1",
        "path": "irrelevant/local/path",
    }
    inventory.write_bytes(stable_json([row]))
    candidate = tmp_path / "candidate"
    build_candidate(workspace, candidate, "synthetic-r1", CASES, inventory)
    inputs = json.loads((candidate / "inputs.json").read_bytes())
    assert inputs["source_documents"] == [
        {key: value for key, value in row.items() if key != "path"}
    ]
    # Read the actual Stage 1 inventory without approving any scientific content.
    documents = source_documents(
        ROOT / "curation/alcohol_flush/acquisition.json",
        {"ncbi-refsnp-rs671", "ncbi-clinvar-rs671", "crabb-1989"},
    )
    assert len(documents) == 3 and all(len(item.sha256) == 64 for item in documents)
    assert any(item.type == "excerpt" for item in documents)
    with pytest.raises(ValueError, match="missing published sources"):
        source_documents(inventory, {"absent-source"})


# CLI lifecycle (the module-entrypoint smoke test lives in Stage 3).


def test_cli_complete_lifecycle_and_understandable_failure(
    workspace: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    candidate = tmp_path / "candidate"
    assert (
        main(
            [
                "build",
                str(workspace),
                str(candidate),
                "--release-id",
                "cli-r1",
                "--cases",
                str(CASES),
            ]
        )
        == 0
    )
    assert "Built candidate cli-r1" in capsys.readouterr().out
    assert main(["preview", str(candidate)]) == 0
    output = capsys.readouterr().out
    assert (candidate / "preview.md").read_text(encoding="utf-8") in output
    fingerprint = output.rsplit("Manifest SHA-256: ", 1)[1].strip()
    assert fingerprint == sha256((candidate / "manifest.json").read_bytes())
    assert (
        main(
            [
                "approve-release",
                str(candidate),
                str(workspace),
                "--reviewer",
                "fictional",
                "--rationale",
                "Synthetic test only.",
                "--fingerprint",
                fingerprint,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["manifest_sha256"] == fingerprint
    releases = tmp_path / "releases"
    assert (
        main(["publish", str(candidate), str(workspace), "--releases", str(releases)])
        == 0
    )
    assert "Published and verified:" in capsys.readouterr().out
    assert main(["verify-release", str(releases / "cli-r1")]) == 0
    assert "all file hashes match" in capsys.readouterr().out
    (candidate / "catalog.json").write_bytes(b"{}")
    with pytest.raises(SystemExit) as error:
        main(["preview", str(candidate)])
    assert (
        error.value.code == 2
        and "Integrity check failed: catalog.json" in capsys.readouterr().err
    )
