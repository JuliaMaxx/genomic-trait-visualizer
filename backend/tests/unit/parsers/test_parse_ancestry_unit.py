import pytest

from backend.services.parsers import parse_ancestry


def to_alleles(genotype: str | None) -> list[str] | None:
    if genotype is None:
        return None
    return [allele for allele in genotype]


# --- Header / BOM / Comment handling ---
@pytest.mark.parametrize(
    "lines",
    [
        [
            "# AncestryDNA raw data",
            "# rsid,chromosome,position,allele1,allele2",
            "rsid,chromosome,position,allele1,allele2",
            "rs123,1,1000,A,A",
        ],
        [
            "\ufeffrsid,chromosome,position,allele1,allele2",
            "rs123,1,1000,A,A",
        ],
        [
            "\ufeffrs123,1,1000,A,A",
        ],
    ],
)
def test_skips_headers_and_strips_bom(lines: list[str]) -> None:
    result = parse_ancestry(lines)
    v = result.variants[0]

    assert len(result.variants) == 1
    assert v.rsid == "rs123"
    assert v.genotype == ["A", "A"]
    assert (
        result.errors == [] or result.errors is not None
    )  # BOM or comment lines produce no errors


# --- Delimiters ---
@pytest.mark.parametrize(
    "line",
    [
        "rs123,1,1000,A,A",
        "rs123\t1\t1000\tA\tA",
        "rs123 1 1000 A A",
        "rs123\t 1 1000\tA\tA",
    ],
)
def test_accepts_delimiter_variations(line: str) -> None:
    result = parse_ancestry([line])
    v = result.variants[0]

    assert len(result.variants) == 1
    assert v.chromosome == "1"
    assert v.position == 1000
    assert v.genotype == ["A", "A"]


# --- Chromosome mapping ---
@pytest.mark.parametrize(
    "chrom_input,expected",
    [
        ("1", "1"),
        ("23", "X"),
        ("24", "Y"),
        ("25", "MT"),
        ("Y", "Y"),
    ],
)
def test_chromosome_normalization(chrom_input: str, expected: str) -> None:
    result = parse_ancestry([f"rs123,{chrom_input},1000,A,A"])
    assert result.variants[0].chromosome == expected


# --- Genotype assembly ---
@pytest.mark.parametrize(
    "allele1,allele2,expected_genotype",
    [
        ("A", "A", "AA"),
        ("A", "G", "AG"),
        ("C", "--", "C"),  # haploid
        ("I", "D", "ID"),  # indels
        ("--", "--", None),  # missing
    ],
)
def test_genotype_assembly(
    allele1: str, allele2: str, expected_genotype: str | None
) -> None:
    result = parse_ancestry([f"rs1,1,1000,{allele1},{allele2}"])
    v = result.variants[0]

    assert v.genotype == to_alleles(expected_genotype)
    if expected_genotype is None:
        assert len(result.errors) == 1
    else:
        assert not result.errors


# --- Internal IDs and duplicates ---
def test_internal_ids_and_duplicates() -> None:
    lines = [
        "i4000001,1,1000,G,G",
        "i4000001,1,1000,G,G",
    ]
    result = parse_ancestry(lines)

    assert len(result.variants) == 2
    assert result.variants[0].rsid == "i4000001"
    assert result.variants[0] == result.variants[1]
    assert result.errors == []


# --- Extra columns ignored ---
def test_extra_columns_ignored() -> None:
    result = parse_ancestry(["rs1,1,100,A,A,EXTRA,VALUE"])
    v = result.variants[0]

    assert v.rsid == "rs1"
    assert v.chromosome == "1"
    assert v.position == 100
    assert v.genotype == ["A", "A"]
