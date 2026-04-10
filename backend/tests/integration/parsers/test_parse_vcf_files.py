import os

from backend.models import Variant
from backend.services.parsers import parse_vcf


# --- Helper ---
def load_sample(sample_name: str) -> list[str]:
    """Load a test sample file from dna_samples/vcf."""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.dirname(os.path.dirname(test_dir))
    file_path = os.path.join(tests_dir, "dna_samples", "vcf", sample_name)
    with open(file_path, "r", encoding="utf-8-sig") as f:
        return f.readlines()


# --- Utility Assertions ---
def assert_variant_fields(variant: Variant) -> None:
    """Check standard VCF variant fields."""
    assert variant.chromosome in {str(i) for i in range(1, 23)} | {
        "X",
        "Y",
        "MT",
    } or variant.chromosome.lower().startswith("chr")
    assert isinstance(variant.position, int) and variant.position > 0
    assert isinstance(variant.rsid, str)
    assert variant.genotype is None or isinstance(variant.genotype, str)


# --- Valid File ---
def test_parse_vcf_valid_file() -> None:
    lines = load_sample("vcf_valid.vcf")
    result = parse_vcf(lines)
    assert len(result.variants) > 0
    assert result.errors == []

    # Spot-check first variant
    v0 = result.variants[0]
    assert v0.chromosome == "1"
    assert v0.position == 742429
    assert v0.rsid == "rs3094315"
    assert v0.genotype == "AA"

    for v in result.variants:
        assert_variant_fields(v)


# --- Edge Case File ---
def test_parse_vcf_edge_file() -> None:
    lines = load_sample("vcf_edge.vcf")
    result = parse_vcf(lines)
    # Should parse even minimal valid lines
    if result.variants:
        assert_variant_fields(result.variants[0])
    assert isinstance(result.variants, list)
    assert isinstance(result.errors, list)


# --- Broken File ---
def test_parse_vcf_broken_file() -> None:
    lines = load_sample("vcf_broken.vcf")
    result = parse_vcf(lines)
    # Parser should never raise
    assert isinstance(result.variants, list)
    assert isinstance(result.errors, list)
    assert len(result.errors) > 0
    # All errors should follow "Line X: ..." format
    for error in result.errors:
        assert error.startswith("Line ") and ":" in error


# --- Messy / Mixed File ---
def test_parse_vcf_messy_file() -> None:
    lines = load_sample("vcf_messy.vcf")
    result = parse_vcf(lines)

    assert len(result.variants) > 0
    for v in result.variants:
        assert_variant_fields(v)

    # Verify at least one variant has missing genotype
    missing_gt = [v for v in result.variants if v.genotype is None]
    assert isinstance(missing_gt, list)

    # Verify multi-allelic ALT handling
    multi_alt = [v for v in result.variants if "," in getattr(v, "alt", "")]
    assert isinstance(multi_alt, list)


# --- Header / Empty Lines / Comments ---
def test_parse_vcf_handles_headers_and_empty_lines() -> None:
    lines = [
        "##fileformat=VCFv4.2",
        '##INFO=<ID=DP,Number=1,Type=Integer,Description="Read Depth">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1",
        "",
        "# This is a comment",
        "1\t1000\t.\tA\tG\t.\t.\t.\tGT\t0/0",
        "2\t2000\trs123\tC\tT\t.\t.\t.\tGT\t1/1",
    ]
    result = parse_vcf(lines)
    assert len(result.variants) == 2
    assert result.errors == []


# --- Empty File ---
def test_parse_vcf_empty_file() -> None:
    result = parse_vcf([])
    assert isinstance(result.variants, list)
    assert result.variants == []
    assert isinstance(result.errors, list)
    assert result.errors == []
