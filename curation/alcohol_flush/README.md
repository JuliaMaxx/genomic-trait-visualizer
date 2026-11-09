# Alcohol Flushing — rs671 Reference Trait

## Overview

I chose alcohol flushing as the first trait for developing the new scientific curation pipeline.

The trait is associated with a genetic variant called **rs671**, located in the **ALDH2** gene. This gene is involved in alcohol metabolism.

Research shows that the A allele of rs671 is associated with reduced ALDH2 enzyme function and with alcohol flushing in certain populations.

However, having a particular genotype does not guarantee that someone will or will not experience flushing.

The goal is to document the scientific evidence and use it to design a more reliable trait interpretation system.

## 1. Scientific sources

The reference trait is based on the following six source documents. All are currently available in `sources/`; none are archived.

| Source                                                                                                                                                                                       | Local file                                                     | Purpose                                                                                                       |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| [NCBI dbSNP — rs671](https://www.ncbi.nlm.nih.gov/snp/rs671)                                                                                                                                 | [rs671-refsnp.json](sources/rs671-refsnp.json)                 | Identifies the variant, its alleles and genomic location                                                      |
| [NCBI ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/variation/18390/)                                                                                                                        | [rs671-clinvar-mapping.xml](sources/rs671-clinvar-mapping.xml) | Molecular mapping excerpt providing additional variant identifiers and representations                        |
| [Crabb et al. (1989)](https://doi.org/10.1172/JCI113875)                                                                                                                                     | [crabb-1989-excerpt.txt](sources/crabb-1989-excerpt.txt)       | Saved excerpt from the study investigating ALDH2 variants and enzyme function                                 |
| [Cho et al. (2023)](https://doi.org/10.1186/s12864-023-09721-7)                                                                                                                              | [cho-2023.xml](sources/cho-2023.xml)                           | Article investigating genetic associations with alcohol flushing in Chinese and Korean male study populations |
| [Cho et al. (2023), Supplementary Material 1](https://media.springernature.com/original/springer-static/esm/art%3A10.1186%2Fs12864-023-09721-7/MediaObjects/12864_2023_9721_MOESM1_ESM.xlsx) | [cho-2023-supplement1.xlsx](sources/cho-2023-supplement1.xlsx) | Supplementary spreadsheet containing tables supporting the article                                            |
| [Cho et al. (2023), Supplementary Material 2](https://static-content.springer.com/esm/art%3A10.1186%2Fs12864-023-09721-7/MediaObjects/12864_2023_9721_MOESM2_ESM.docx)                       | [cho-2023-supplement2.docx](sources/cho-2023-supplement2.docx) | Supporting reference for population selection and flushing questions; excluded from the extraction experiment |

The exact findings, citations, genomic coordinates and unresolved questions are recorded in `dossier.json`.

## 2. What the research suggests

The main findings used in this reference trait are:

- The rs671 A allele is associated with reduced ALDH2 enzyme function.
- The variant is associated with alcohol flushing in the populations examined by Cho et al.
- The association does not mean that everyone with the A allele experiences flushing.
- The available evidence does not provide a validated personal probability or symptom-severity prediction for this application.

The scientific studies also have limitations. For example, Cho's research concerns specific populations and uses reported flushing symptoms rather than directly measuring each participant's enzyme activity.

## 3. Proposed interpretation

Instead of assigning arbitrary scores to genotypes, the new approach will initially describe the presence of the specified allele.

For a verified, compatible rs671 genotype:

| Genotype                     | Interpretation                      |
| ---------------------------- | ----------------------------------- |
| GG                           | No copies of the specified A allele |
| AG / GA                      | One copy of the A allele            |
| AA                           | Two copies of the A allele          |
| Missing or incompatible data | Interpretation unavailable          |

The interpretation will explain the research-supported association without claiming to predict a person's individual symptoms.

These are proposed requirements, not yet implemented or scientifically approved results.

## 4. Research files

- [dossier.json](dossier.json) — Draft scientific evidence, variant information, references and unresolved questions.
- [stage2-draft.json](stage2-draft.json) — A score-free, unapproved schema example using the mapping and functional subset; see [Stage 2 contracts](../stage2-contracts.md).
- [acquisition.json](acquisition.json) — Information about the saved research files, including their original locations and checksums.
- [expected-cases.md](expected-cases.md) — Separate draft cases, distinguishing source-based allele counts from proposed software handling policies.
- [stage4-expected-cases.json](stage4-expected-cases.json) — Offline transcription of those expectations, with conservative software policies and duplicate handling explicitly deferred. This file grants no scientific approval.
- [sources/](sources/) — All six current source documents listed above, including the ClinVar and Crabb excerpts.
- [comparison-protocol-bachelors.md](../comparison-protocol-bachelors.md) — Plan for comparing manual and semi-automatic scientific data extraction.

## 5. Planned use in the project

This trait will serve as a development example for the new curation pipeline.

The initial experiment will use three saved documents:

- NCBI rs671 variant record.
- Cho et al. article.
- Cho et al. supplementary spreadsheet.

The Crabb and ClinVar excerpts and Cho Supplementary Material 2 are supporting scientific references outside the initial extraction experiment. The expected-case specification is also excluded from extraction inputs.

The goal is to compare scientific information extracted manually with information extracted by the future pipeline and then reviewed by a human.

The experimental method is described in [comparison-protocol-bachelors.md](../comparison-protocol-bachelors.md).

## 6. What still needs to be reviewed

Before using this trait in the new interpretation engine, I need to:

- Verify the rs671 allele mappings against NCBI.
- Check the functional findings reported by Crabb.
- Check the association and population information reported by Cho.
- Confirm that the proposed genotype interpretation is supported by the evidence.
- Confirm that the intended application behavior is appropriate.

Not every uncertainty needs to be resolved before defining the new data models, but unsupported claims must not become approved interpretation rules.

## Summary

This reference trait provides a researched example for designing the new curation system.

The main objective is to make scientific evidence traceable and to separate reported genetic associations from unsupported personal predictions.
