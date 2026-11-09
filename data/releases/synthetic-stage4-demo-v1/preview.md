# Publication preview: Fictional allele-count demonstration

Trait: `synthetic_allele` | Category: nutrition

Fictional software example only; this marker and its claims are not scientific evidence.

## Scientific claims

### synthetic-reviewed-claim

This fictional marker can illustrate counting a specified allele.

Scope: Fictional software tests only; no claim about a real variant or person.

Evidence: synthetic-finding

- Fictional data cannot support a personal prediction.

## Sources and evidence locations

### synthetic-study: Fictional study for testing; not a scientific publication

- source_type: other

**synthetic-finding**: A fictional teaching source describes the A/G marker used in these software tests.

- claim_type: "study_limitation"
- source_location: {"section": "Fictional results"}

## Interpretation

Strategy: `allele_count`

Supporting claims: synthetic-reviewed-claim

Counted allele: `A`

Required representation:

```json
{
  "rsid": "rs12345678",
  "placements": [
    {
      "genome_build": "GRCh38",
      "chromosome": "1",
      "position": 101,
      "sequence_accession": "NC_000001.11"
    }
  ],
  "orientation": "forward_genomic",
  "coordinate_system": "1-based",
  "ploidy": 2,
  "alleles": [
    "A",
    "G"
  ]
}
```

| Genotype | Copies |
| --- | --- |
| GG | 0 |
| AG | 1 |
| AA | 2 |

Missing/incompatible input policy: `withhold`.

## Reviewed explanations

### synthetic-explanation (simple_explanation; general)

Understanding context (fictional example)

This fictional example counts A copies only when every required representation field is known and compatible. Counts are not symptom probabilities.

Claims: synthetic-reviewed-claim

### synthetic-result-0 (outcome_summary; 0)

Zero A copies at this fictional marker.

Claims: synthetic-reviewed-claim

### synthetic-result-1 (outcome_summary; 1)

One A copy at this fictional marker.

Claims: synthetic-reviewed-claim

### synthetic-result-2 (outcome_summary; 2)

Two A copies at this fictional marker.

Claims: synthetic-reviewed-claim

### synthetic-result-unavailable (outcome_summary; unavailable)

No count is available for missing or incompatible data; this does not mean zero copies.

Claims: synthetic-reviewed-claim

## Independent verification

Case set: fictional-allele-v1 (synthetic)

Fictional cases manually specified for software testing; not scientific approval.

Required cases: PASS

- **S1-GRCh38**: passed. Fictional arithmetic test, not scientific evidence.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "GG", "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": 0, "reason": null, "status": "evaluated"}`.
  Actual: `{"copies": 0, "reason": null, "status": "evaluated"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-0.
- **S2-GRCh38**: passed. Fictional arithmetic test, not scientific evidence.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "AG", "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": 1, "reason": null, "status": "evaluated"}`.
  Actual: `{"copies": 1, "reason": null, "status": "evaluated"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-1.
- **S3-GRCh38**: passed. Fictional arithmetic test, not scientific evidence.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "GA", "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": 1, "reason": null, "status": "evaluated"}`.
  Actual: `{"copies": 1, "reason": null, "status": "evaluated"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-1.
- **S4-GRCh38**: passed. Fictional arithmetic test, not scientific evidence.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "AA", "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": 2, "reason": null, "status": "evaluated"}`.
  Actual: `{"copies": 2, "reason": null, "status": "evaluated"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-2.
- **P1-absent**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `null`.
  Expected: `{"copies": null, "reason": "missing_genotype", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "missing_genotype", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P1-no-call**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": null, "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": null, "reason": "missing_genotype", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "missing_genotype", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P2-partial**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "G/.", "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": null, "reason": "invalid_genotype", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "invalid_genotype", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P3-malformed**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "AA?", "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": null, "reason": "invalid_genotype", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "invalid_genotype", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P4-unsupported**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "GC", "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": null, "reason": "unsupported_allele", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "unsupported_allele", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P5-wrong-position**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "AG", "orientation": "forward_genomic", "ploidy": 2, "position": 102, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": null, "reason": "incompatible_representation", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "incompatible_representation", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P6-missing-build**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": null, "genotype": "AG", "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": null, "reason": "missing_representation", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "missing_representation", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P6-missing-orientation**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "AG", "orientation": null, "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": null, "reason": "missing_representation", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "missing_representation", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P6-unsupported-build**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "unverified", "genotype": "AG", "orientation": "forward_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": null, "reason": "unsupported_build", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "unsupported_build", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P7-reverse-orientation**: passed. Fictional software test. No biological inference or provider handling is asserted.
  Input: `{"chromosome": "1", "coordinate_system": "1-based", "genome_build": "GRCh38", "genotype": "AG", "orientation": "reverse_genomic", "ploidy": 2, "position": 101, "rsid": "rs12345678", "sequence_accession": "NC_000001.11"}`.
  Expected: `{"copies": null, "reason": "unsupported_orientation", "status": "unavailable"}`.
  Actual: `{"copies": null, "reason": "unsupported_orientation", "status": "unavailable"}`.
  Explanation IDs: synthetic-explanation, synthetic-result-unavailable.
- **P8-duplicate-conflicts**: deferred. Stage 1 leaves duplicate-observation handling unresolved. This offline function accepts one explicit observation; parser aggregation belongs to Stage 6.
