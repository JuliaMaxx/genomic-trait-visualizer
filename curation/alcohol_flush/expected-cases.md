# rs671 expected cases

## Scientific expectations

These expectations come from the retained NCBI variant placements and counting the A alleles in a complete diploid genotype. They were authored separately from the dossier's interpretation table and the legacy evaluator; no existing interpretation mapping was used to generate them.

Source: [RefSNP rs671](sources/rs671-refsnp.json), `primary_snapshot_data.placements_with_allele`, entries selected by `seq_id = NC_000012.12` and `NC_000012.11`, then `alleles[].hgvs` and `placement_annot`. [ClinVar](sources/rs671-clinvar-mapping.xml), `Location/SequenceLocation` and `HGVSlist`, provides the corresponding genomic and protein representations.

Use chromosome 12, forward-genomic alleles and 1-based positions:

| Build  | Sequence accession | Position  | Studied substitution |
| ------ | ------------------ | --------- | -------------------- |
| GRCh38 | NC_000012.12       | 111803962 | G>A                  |
| GRCh37 | NC_000012.11       | 112241766 | G>A                  |

Apply each case below at **both** listed placements, with build, locus, orientation and a complete diploid call established independently of the genotype letters.

| Case | Observed alleles | Expected A copies | Bounded meaning                          |
| ---- | ---------------- | ----------------- | ---------------------------------------- |
| S1   | G, G             | 0                 | This particular A allele is absent.      |
| S2   | A, G             | 1                 | One copy of this A allele is present.    |
| S3   | G, A             | 1                 | The same unphased allele count as S2.    |
| S4   | A, A             | 2                 | Two copies of this A allele are present. |

The two build placements describe the same variant, so equivalent calls have the same allele count. No coordinate conversion algorithm is specified here.

Linking the A allele to reduced ALDH2 function additionally requires the naming correspondence in ClinVar (`OtherNameList`, `HGVSlist`) and [Crabb's original paper](https://www.jci.org/articles/view/113875/scanned-page/315), printed page 315, Results and Discussion, first paragraph in the left column. The [retained Crabb excerpt](sources/crabb-1989-excerpt.txt) contains only the abstract's dominance conclusion. These sources still require human review. Copy count does not establish personal flushing probability, severity or an enzyme-activity percentage; zero copies does not exclude flushing.

## Proposed software policies — to be finalized later

The following are conservative handling proposals, not conclusions reported by the studies. Examples describe observations; they do not define accepted file encodings, API states or reason codes.

| Case | Observation                                                                                  | Proposed handling                                                                                                               |
| ---- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| P1   | rs671 absent, or present with an empty/no-call genotype                                      | Withhold the allele count; missing information is not zero copies.                                                              |
| P2   | Partial call such as `G/.`, or only one reported allele                                      | Withhold a complete diploid count; do not fill the missing allele.                                                              |
| P3   | Malformed text such as `AA?`, or four alleles such as `ACGT`                                 | Withhold interpretation; do not extract a plausible genotype from invalid text.                                                 |
| P4   | A call containing an allele outside the studied G/A pair, such as G/C                        | Withhold this model's annotation; do not infer a biological meaning for the unsupported allele.                                 |
| P5   | rs671 with the wrong chromosome, wrong position, or GRCh38 paired with the GRCh37 coordinate | Withhold interpretation until the locus and build agree; the rsID alone is insufficient.                                        |
| P6   | Unknown or unsupported build, or unknown allele orientation                                  | Withhold interpretation until compatibility is established.                                                                     |
| P7   | A reverse-strand C/T call                                                                    | Require a separately verified transformation before using the forward-genomic cases; do not guess orientation from the letters. |
| P8   | Conflicting calls for the same locus, such as GG and AA                                      | Withhold the allele count until conflict handling is defined; do not silently select the last row.                              |

Provider conventions, accepted encodings and ploidy, strand transformations, duplicate handling, and exact unavailable-result states remain future software decisions. This file does not authorize runtime changes.
