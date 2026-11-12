"""Tests for Stage 6 DNA ingestion and compatibility matching.

Uses fictional 23andMe Build 37 data to verify valid, missing, invalid,
and conflicting calls, plus compatibility with reviewed rules.
"""

from pathlib import Path
from typing import Any

import pytest

from backend.models.interpretation import AlleleCountInterpretation
from backend.models.published_catalog import PublishedTrait, TraitCatalog
from backend.services import dna_service
from backend.services.trait_curation.offline import Observation, evaluate

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "backend/tests/dna_samples/stage6/23andme_build37.txt"
RELEASE = ROOT / "data/releases/synthetic-stage4-demo-v1/catalog.json"
ROW = "rs12345678\t1\t101\tGA"


@pytest.fixture
def dna_lines() -> list[str]:
    return SAMPLE.read_text(encoding="utf-8").splitlines()


@pytest.fixture
def reviewed_trait() -> PublishedTrait:
    # Reuse the published fictional rule table and explanations. Only the test
    # placement changes; position 101 is fictional, not an asserted real mapping.
    data = (
        TraitCatalog.model_validate_json(RELEASE.read_bytes())
        .traits[0]
        .model_dump(mode="json")
    )
    placement = data["interpretation"]["requirements"]["placements"][0]
    placement.update(genome_build="GRCh37", sequence_accession="NC_000001.10")
    return PublishedTrait.model_validate(data)


def ingest(lines: list[str]) -> Any:
    # Resolve at runtime so missing Stage 6 code gives a failing assertion,
    # not a collection error. There is deliberately no fake implementation.
    function = getattr(dna_service, "ingest_dna", None)
    assert callable(function), "Stage 6 contract missing: dna_service.ingest_dna(lines)"
    return function(lines)


def match(ingestion: Any, trait: PublishedTrait) -> Any:
    assert isinstance(trait.interpretation, AlleleCountInterpretation)
    function = getattr(dna_service, "match_observation", None)
    assert callable(function), "Stage 6 contract missing: dna_service.match_observation"
    return function(ingestion, trait.interpretation.requirements)


def assert_withheld(result: Any, trait: PublishedTrait) -> None:
    assert result.status != "usable"
    assert result.observation is None
    assert result.diagnostics
    evaluated = evaluate(trait, result.observation)
    assert evaluated.status == "unavailable" and evaluated.copies is None
    assert {text.result_key for text in evaluated.explanations} == {None, "unavailable"}


def test_supported_file_preserves_raw_representation_and_matches_reviewed_rule(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    ingestion = ingest(dna_lines)
    assert ingestion.provider == "23andme"
    assert ingestion.diagnostics == []
    assert len(ingestion.observations) == 2
    raw = ingestion.observations[0]
    assert isinstance(raw, Observation)
    assert (raw.rsid, raw.genotype, raw.chromosome, raw.position) == (
        "rs12345678",
        "GA",
        "1",
        101,
    )
    assert raw.genome_build == "GRCh37"
    assert raw.orientation == "forward_genomic"
    assert raw.coordinate_system == "1-based" and raw.ploidy == 2

    result = match(ingestion, reviewed_trait)
    assert result.status == "usable" and result.diagnostics == []
    assert result.observation == Observation(
        genotype="AG",
        rsid="rs12345678",
        genome_build="GRCh37",
        chromosome="1",
        position=101,
        sequence_accession="NC_000001.10",
        orientation="forward_genomic",
        coordinate_system="1-based",
        ploidy=2,
    )
    evaluated = evaluate(reviewed_trait, result.observation)
    assert evaluated.status == "evaluated" and evaluated.copies == 1
    assert {text.result_key for text in evaluated.explanations} == {None, "1"}


@pytest.mark.parametrize("genotype", ["AG", "GA"])
def test_equivalent_diploid_calls_have_the_same_usable_observation(
    dna_lines: list[str], reviewed_trait: PublishedTrait, genotype: str
) -> None:
    ingestion = ingest(
        [line.replace(ROW, f"rs12345678\t1\t101\t{genotype}") for line in dna_lines]
    )
    assert ingestion.observations[0].genotype == genotype
    result = match(ingestion, reviewed_trait)
    assert result.status == "usable"
    assert result.observation.genotype == "AG"
    assert evaluate(reviewed_trait, result.observation).copies == 1


def test_absent_variant_is_not_replaced_by_another_rsid_at_the_same_locus(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    ingestion = ingest([line.replace("rs12345678", "rs87654321") for line in dna_lines])
    result = match(ingestion, reviewed_trait)
    assert result.status == "absent"
    assert_withheld(result, reviewed_trait)


def test_parser_diagnostics_survive_ingestion_without_hiding_valid_observations(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    ingestion = ingest(dna_lines + ["rs99999992\t1\tnot-a-position\tAA"])
    assert any("position" in message.lower() for message in ingestion.diagnostics)
    result = match(ingestion, reviewed_trait)
    assert result.status == "usable"
    assert evaluate(reviewed_trait, result.observation).copies == 1


@pytest.mark.parametrize(
    "genotype,status",
    [
        ("--", "no_call"),
        ("AA?", "partial"),
        ("A-", "partial"),
        ("ZZ", "invalid"),
        ("AAZ", "invalid"),
    ],
)
def test_problematic_calls_keep_raw_text_and_never_receive_a_count(
    dna_lines: list[str], reviewed_trait: PublishedTrait, genotype: str, status: str
) -> None:
    ingestion = ingest(
        [line.replace(ROW, f"rs12345678\t1\t101\t{genotype}") for line in dna_lines]
    )
    assert ingestion.observations[0].genotype == genotype
    result = match(ingestion, reviewed_trait)
    assert result.status == status
    assert_withheld(result, reviewed_trait)


@pytest.mark.parametrize(
    "rows,status",
    [
        ([ROW, ROW], "usable"),
        ([ROW, "rs12345678\t1\t101\tAG"], "usable"),
        (["rs12345678\t1\t101\tAA", "rs12345678\t1\t101\tGG"], "conflicting"),
        ([ROW, "rs12345678\t1\t102\tGA"], "conflicting"),
    ],
    ids=["identical-calls", "equivalent-calls", "different-calls", "different-loci"],
)
def test_duplicate_resolution_does_not_depend_on_row_order(
    dna_lines: list[str], reviewed_trait: PublishedTrait, rows: list[str], status: str
) -> None:
    header = [line for line in dna_lines if line.startswith("#")]
    first = ingest(header + rows)
    second = ingest(header + list(reversed(rows)))
    # All source evidence survives; matching produces one deterministic decision.
    assert len(first.observations) == len(second.observations) == 2
    assert sorted(row.genotype for row in first.observations) == sorted(
        row.genotype for row in second.observations
    )
    forward = match(first, reviewed_trait)
    backward = match(second, reviewed_trait)
    assert forward.status == backward.status == status
    assert forward.observation == backward.observation
    if status == "usable":
        assert forward.observation.genotype == "AG"
        assert evaluate(reviewed_trait, forward.observation).copies == 1
    else:
        assert_withheld(forward, reviewed_trait)
        assert_withheld(backward, reviewed_trait)


@pytest.mark.parametrize("chromosome,position", [("2", 101), ("1", 102)])
def test_matching_rsid_cannot_override_a_wrong_chromosome_or_position(
    dna_lines: list[str], reviewed_trait: PublishedTrait, chromosome: str, position: int
) -> None:
    ingestion = ingest(
        [
            line.replace(ROW, f"rs12345678\t{chromosome}\t{position}\tGA")
            for line in dna_lines
        ]
    )
    raw = ingestion.observations[0]
    assert (raw.chromosome, raw.position) == (chromosome, position)
    result = match(ingestion, reviewed_trait)
    assert result.status == "incompatible"
    assert_withheld(result, reviewed_trait)


def test_matching_coordinates_do_not_override_a_different_rule_build(
    dna_lines: list[str],
) -> None:
    # The unchanged fictional release requires GRCh38 at the same numeric locus.
    other_build = TraitCatalog.model_validate_json(RELEASE.read_bytes()).traits[0]
    ingestion = ingest(dna_lines)
    assert ingestion.observations[0].genome_build == "GRCh37"
    result = match(ingestion, other_build)
    assert result.status == "incompatible"
    assert_withheld(result, other_build)


@pytest.mark.parametrize("metadata", ["build", "orientation"])
def test_missing_metadata_is_not_filled_from_the_rule_or_provider_name(
    dna_lines: list[str], reviewed_trait: PublishedTrait, metadata: str
) -> None:
    marker = "assembly build" if metadata == "build" else "plus strand"
    ingestion = ingest([line for line in dna_lines if marker not in line])
    raw = ingestion.observations[0]
    assert (
        getattr(raw, "genome_build" if metadata == "build" else "orientation") is None
    )
    result = match(ingestion, reviewed_trait)
    assert result.status == "unresolved"
    assert_withheld(result, reviewed_trait)


def test_contradictory_build_headers_cannot_be_resolved_by_selecting_a_match(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    other_build = "# We are using reference human assembly build 38."
    for lines in ([other_build] + dna_lines, dna_lines + [other_build]):
        result = match(ingest(lines), reviewed_trait)
        assert result.status == "unresolved"
        assert_withheld(result, reviewed_trait)


def test_reverse_orientation_is_preserved_and_never_flipped_to_match(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    ingestion = ingest(
        [line.replace("plus strand", "minus strand") for line in dna_lines]
    )
    assert ingestion.observations[0].orientation == "reverse_genomic"
    result = match(ingestion, reviewed_trait)
    assert result.status == "incompatible"
    assert_withheld(result, reviewed_trait)


def test_unreviewed_snv_allele_is_withheld(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    ingestion = ingest(
        [line.replace(ROW, "rs12345678\t1\t101\tAC") for line in dna_lines]
    )
    assert ingestion.observations[0].genotype == "AC"
    result = match(ingestion, reviewed_trait)
    assert result.status == "incompatible"
    assert_withheld(result, reviewed_trait)


@pytest.mark.parametrize("genotype", ["A", "AAA", "ID"])
def test_unsupported_ploidy_or_indel_never_becomes_a_diploid_snv(
    dna_lines: list[str], reviewed_trait: PublishedTrait, genotype: str
) -> None:
    ingestion = ingest(
        [line.replace(ROW, f"rs12345678\t1\t101\t{genotype}") for line in dna_lines]
    )
    assert ingestion.observations[0].genotype == genotype
    result = match(ingestion, reviewed_trait)
    assert result.status == "unsupported"
    assert_withheld(result, reviewed_trait)


def test_non_autosomal_row_is_outside_the_supported_subset(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    ingestion = ingest(
        [line.replace(ROW, "rs12345678\tX\t101\tGA") for line in dna_lines]
    )
    assert ingestion.observations[0].chromosome == "X"
    result = match(ingestion, reviewed_trait)
    assert result.status == "unsupported"
    assert_withheld(result, reviewed_trait)


def test_sequence_accession_cannot_be_borrowed_from_a_rule_to_force_compatibility(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    data = reviewed_trait.model_dump(mode="json")
    data["interpretation"]["requirements"]["placements"][0][
        "sequence_accession"
    ] = "NC_000001.11"  # GRCh38 accession is incompatible with this Build 37 upload.
    wrong_accession = PublishedTrait.model_validate(data)
    result = match(ingest(dna_lines), wrong_accession)
    assert result.status == "incompatible"
    assert_withheld(result, wrong_accession)


@pytest.mark.parametrize("provider", ["MyHeritage", "unspecified", "VCF"])
def test_unverified_provider_representations_are_explicitly_gated(
    dna_lines: list[str], provider: str
) -> None:
    if provider == "MyHeritage":
        lines = [line.replace("23andMe", "MyHeritage") for line in dna_lines]
    elif provider == "unspecified":
        lines = [line for line in dna_lines if "23andMe" not in line]
    else:
        lines = [
            "##fileformat=VCFv4.2",
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE",
            "1\t101\trs12345678\tG\tA\t.\tPASS\t.\tGT\t0/1",
        ]
    with pytest.raises(ValueError, match="(?i)unsupported"):
        ingest(lines)


@pytest.mark.parametrize(
    "metadata",
    [
        [
            "# Genotypes are reported using the forward strand of the "
            "human reference genome build 37.",
        ],
        [
            "# genotype call oriented with respect to the plus strand "
            "on the human reference sequence.",
            "# We are using reference human assembly ((build37)) "
            "(also known as Annotation Release 104).",
        ],
    ],
    ids=["combined-forward-header", "older-parenthesized-build"],
)
def test_documented_header_wording_is_supported(
    dna_lines: list[str], reviewed_trait: PublishedTrait, metadata: list[str]
) -> None:
    lines = [
        line
        for line in dna_lines
        if "assembly build" not in line and "plus strand" not in line
    ]
    ingestion = ingest(metadata + lines)
    assert all(line in ingestion.metadata for line in metadata)
    result = match(ingestion, reviewed_trait)
    assert result.status == "usable" and result.diagnostics == []
    assert evaluate(reviewed_trait, result.observation).copies == 1


@pytest.mark.parametrize("genotype", ["ag", "ga"])
def test_identifier_case_and_allele_order_can_be_normalized_safely(
    dna_lines: list[str], reviewed_trait: PublishedTrait, genotype: str
) -> None:
    ingestion = ingest(
        [line.replace(ROW, f"RS12345678\t1\t101\t{genotype}") for line in dna_lines]
    )
    assert ingestion.observations[0].genotype == genotype
    result = match(ingestion, reviewed_trait)
    assert result.status == "usable" and result.observation.genotype == "AG"


@pytest.mark.parametrize("genotype", ["AA Z", "A/A", "A|A", "AAZ?", "Z-"])
def test_malformed_genotype_characters_are_never_discarded(
    dna_lines: list[str], reviewed_trait: PublishedTrait, genotype: str
) -> None:
    ingestion = ingest(
        [line.replace(ROW, f"rs12345678\t1\t101\t{genotype}") for line in dna_lines]
    )
    assert ingestion.observations[0].genotype == genotype
    result = match(ingestion, reviewed_trait)
    assert result.status == "invalid"
    assert_withheld(result, reviewed_trait)


@pytest.mark.parametrize("genotype", ["--", "AA?", "ZZ", "A", "ID"])
def test_a_clean_duplicate_does_not_override_an_unusable_row(
    dna_lines: list[str], reviewed_trait: PublishedTrait, genotype: str
) -> None:
    header = [line for line in dna_lines if line.startswith("#")]
    rows = [ROW, f"rs12345678\t1\t101\t{genotype}"]
    forward = match(ingest(header + rows), reviewed_trait)
    backward = match(ingest(header + list(reversed(rows))), reviewed_trait)
    assert forward == backward and forward.status == "conflicting"
    assert_withheld(forward, reviewed_trait)


@pytest.mark.parametrize(
    "row",
    [
        "rs12345678\t1\tbad-position\tAA",
        "rs12345678\t1\t0\tAA",
        "rs12345678\tbad-chromosome\t101\tAA",
        "rs12345678\t1\t101\tAA\t?",
        "rs12345678\t1\t101",
        "rs12345678 1 101 AA",
        "rs12345678\t1 2\t101\tAA",
    ],
)
def test_a_dropped_or_unsupported_row_cannot_be_rescued_by_a_clean_duplicate(
    dna_lines: list[str], reviewed_trait: PublishedTrait, row: str
) -> None:
    header = [line for line in dna_lines if line.startswith("#")]
    for rows in ([row], [ROW, row], [row, ROW]):
        ingestion = ingest(header + rows)
        assert ingestion.diagnostics
        result = match(ingestion, reviewed_trait)
        assert result.status == "invalid"
        assert_withheld(result, reviewed_trait)


@pytest.mark.parametrize(
    "header",
    ["# Genotypes use the minus strand.", "# Genotypes use an unknown strand."],
)
def test_conflicting_orientation_metadata_is_not_selected_by_row_order(
    dna_lines: list[str], reviewed_trait: PublishedTrait, header: str
) -> None:
    for lines in ([header] + dna_lines, dna_lines + [header]):
        ingestion = ingest(lines)
        assert ingestion.observations[0].orientation is None
        result = match(ingestion, reviewed_trait)
        assert result.status == "unresolved"
        assert_withheld(result, reviewed_trait)


@pytest.mark.parametrize("build", ["38", "unknown", "?", "37.1"])
def test_unsupported_upload_builds_are_preserved_and_withheld(
    dna_lines: list[str], reviewed_trait: PublishedTrait, build: str
) -> None:
    ingestion = ingest(
        [line.replace("build 37", f"build {build}") for line in dna_lines]
    )
    assert ingestion.observations[0].genome_build != "GRCh37"
    result = match(ingestion, reviewed_trait)
    assert result.status == "unsupported"
    assert_withheld(result, reviewed_trait)


def test_raw_observations_cannot_bypass_duplicate_matching(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    ingestion = ingest(dna_lines + ["rs12345678\t1\t101\tAA"])
    for observation in ingestion.observations:
        assert observation.sequence_accession is None
        assert evaluate(reviewed_trait, observation).status == "unavailable"
    assert_withheld(match(ingestion, reviewed_trait), reviewed_trait)


def test_explicit_unknown_strand_is_unresolved(
    dna_lines: list[str], reviewed_trait: PublishedTrait
) -> None:
    ingestion = ingest(
        [line.replace("plus strand", "unknown strand") for line in dna_lines]
    )
    assert ingestion.observations[0].orientation == "unknown"
    result = match(ingestion, reviewed_trait)
    assert result.status == "unresolved"
    assert_withheld(result, reviewed_trait)
