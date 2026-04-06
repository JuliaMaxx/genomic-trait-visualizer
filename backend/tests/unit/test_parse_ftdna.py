import pytest

from backend.services.parsers.parser_ftdna import parse_ftdna


# --- Header / BOM / Comment handling ---
@pytest.mark.parametrize(
    "lines",
    [
        [
            "# FTDNA Raw Data",
            "rsid,chromosome,position,allele1,allele2",
            "rs123,1,1000,A,A",
        ],
        [
            "RSID,CHROMOSOME,POSITION,RESULT",
            "rs123,1,1000,AA",
        ],
        [
            "\ufeffrsid,chromosome,position,allele1,allele2",
            "rs123,1,1000,A,A",
        ],
        [
            "\ufeffrs123,1,1000,AA",
        ],
    ],
)
def test_skips_headers_and_strips_bom(lines: list[str]) -> None:
    result = parse_ftdna(lines)
    v = result.variants[0]

    assert len(result.variants) == 1
    assert v.rsid == "rs123"
    assert v.genotype == "AA"


# --- Delimiters ---
@pytest.mark.parametrize(
    "line",
    [
        "rs123,1,1000,A,A",
        "rs123\t1\t1000\tA\tA",
        "rs123 1 1000 A A",
        "rs123\t 1 1000\tA\tA",
        "rs123,1,1000,AA",  # combined format
    ],
)
def test_accepts_delimiter_variations(line: str) -> None:
    result = parse_ftdna([line])
    v = result.variants[0]

    assert len(result.variants) == 1
    assert v.chromosome == "1"
    assert v.position == 1000
    assert v.genotype == "AA"


# --- Chromosome mapping ---
@pytest.mark.parametrize(
    "chrom_input,expected",
    [
        ("1", "1"),
        ("23", "X"),
        ("24", "Y"),
        ("25", "MT"),
        ("Y", "Y"),
        ("MT", "MT"),
    ],
)
def test_chromosome_normalization(chrom_input: str, expected: str) -> None:
    result = parse_ftdna([f"rs123,{chrom_input},1000,A,A"])
    assert result.variants[0].chromosome == expected


# --- Genotype assembly (allele split format) ---
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
def test_genotype_assembly_from_alleles(
    allele1: str, allele2: str, expected_genotype: str | None
) -> None:
    result = parse_ftdna([f"rs1,1,1000,{allele1},{allele2}"])
    v = result.variants[0]

    assert v.genotype == expected_genotype
    if expected_genotype is None:
        assert len(result.errors) == 1
    else:
        assert not result.errors


# --- Genotype parsing (combined result format) ---
@pytest.mark.parametrize(
    "result_value,expected_genotype",
    [
        ("AA", "AA"),
        ("AG", "AG"),
        ("A", "A"),  # haploid
        ("--", None),  # missing
        ("ZZ", None),  # invalid
    ],
)
def test_genotype_from_result_column(
    result_value: str, expected_genotype: str | None
) -> None:
    result = parse_ftdna([f"rs1,1,1000,{result_value}"])
    v = result.variants[0]

    assert v.genotype == expected_genotype
    if expected_genotype is None:
        assert len(result.errors) == 1


# --- Mixed format support ---
def test_mixed_result_and_allele_formats() -> None:
    lines = [
        "rs1,1,1000,A,A",
        "rs2,1,1001,GG",
    ]
    result = parse_ftdna(lines)

    assert len(result.variants) == 2
    assert result.variants[0].genotype == "AA"
    assert result.variants[1].genotype == "GG"


# --- Internal IDs and duplicates ---
def test_internal_ids_and_duplicates() -> None:
    lines = [
        "i4000001,1,1000,G,G",
        "i4000001,1,1000,G,G",
    ]
    result = parse_ftdna(lines)

    assert len(result.variants) == 2
    assert result.variants[0].rsid == "i4000001"
    assert result.variants[0] == result.variants[1]
    assert result.errors == []


# --- Extra columns ignored ---
def test_extra_columns_ignored() -> None:
    result = parse_ftdna(["rs1,1,100,A,A,EXTRA,VALUE"])
    v = result.variants[0]

    assert v.rsid == "rs1"
    assert v.chromosome == "1"
    assert v.position == 100
    assert v.genotype == "AA"
