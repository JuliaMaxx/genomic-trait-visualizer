# Thesis experiment: manual vs. semi-automatic scientific data curation

**Status:** Draft plan. The comparison has not been conducted yet.

## 1. Research objective

My project uses scientific publications and genetic databases to explain DNA variants. Before this information can be used by the application, it needs to be collected, checked and stored in a consistent format. Doing this manually for many traits could take considerable time.

The aim of this experiment is to answer:

> Can a semi-automatic extraction pipeline reduce the amount of human work needed to curate genetic evidence while maintaining accuracy, completeness and source traceability?

This experiment evaluates **data extraction and curation**, not whether the application can predict an individual's traits or symptoms.

## 2. Methods being compared

I will compare two approaches using the same source documents and the same required information.

| Method           | Process                                                                                                      |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| **A — Manual**   | I read the documents and record the required information myself.                                             |
| **B — Assisted** | The pipeline extracts the information, and I review its output, correcting or rejecting anything inaccurate. |

For both methods, I will save the initial result and the final reviewed result. This will let me distinguish **extraction quality** from the quality achieved after human corrections.

## 3. Development example: rs671

The first example is **rs671 in the ALDH2 gene**, which is associated with alcohol metabolism and flushing. It is used to develop the extraction process and test the evaluation method.

The rs671 research contains **six saved scientific source files**, listed in [acquisition.json](alcohol_flush/acquisition.json). Three are **experiment inputs**, while three are **supporting references**:

| Document                        | File                                              | Role                 |
| ------------------------------- | ------------------------------------------------- | -------------------- |
| NCBI RefSNP record              | `alcohol_flush/sources/rs671-refsnp.json`         | Experiment           |
| Cho et al. (2023) article       | `alcohol_flush/sources/cho-2023.xml`              | Experiment           |
| Cho et al. supplementary tables | `alcohol_flush/sources/cho-2023-supplement1.xlsx` | Experiment           |
| NCBI ClinVar mapping excerpt    | `alcohol_flush/sources/rs671-clinvar-mapping.xml` | Supporting reference |
| Crabb et al. (1989) excerpt     | `alcohol_flush/sources/crabb-1989-excerpt.txt`    | Supporting reference |
| Cho et al. supplementary methods | `alcohol_flush/sources/cho-2023-supplement2.docx` | Supporting reference |

The **initial extraction comparison uses only the three experiment files**, for both manual and assisted methods. The ClinVar and Crabb excerpts and Cho Supplementary Material 2 help document and review the wider scientific interpretation; they are not supplied during the measured extraction task. The research dossier, README, existing `traits.json`, supporting references and prepared answers must not be provided as hints during extraction. No additional sources will be consulted during the measured task.

The eight tasks for the rs671 example are:

| ID  | Information to extract                                                                                                       |
| --- | ---------------------------------------------------------------------------------------------------------------------------- |
| T01 | rs671 position and alleles in GRCh38                                                                                         |
| T02 | rs671 position and alleles in GRCh37, including the relationship between the two representations                             |
| T05 | Study populations, flushing questionnaire and definition of flushing used by Cho                                             |
| T06 | Proportions of rs671 A carriers among flushers and non-flushers in the Chinese cohort (CKB)                                  |
| T07 | Corresponding carrier proportions and population information for the Korean cohort (KoGES)                                   |
| T08 | rs671 results in Cho's Table 1, including alleles, reported statistics and any interpretation uncertainty                    |
| T09 | More precise rs671 values in Supplementary Table 8; recognize that this is the same study result, not an independent finding |
| T10 | Differences or unclear information in reported sample totals and statistical methods                                         |

The original task IDs are retained to match the Stage 1 research notes. **T03 (ClinVar) and T04 (Crabb) are not evaluated**, because their source files are excluded from this extraction task. Their omission is not an extraction error.

For every task, the output should include the relevant source location. Missing or unclear information must be identified rather than guessed. In particular, reported statistics must not be converted into personal probabilities without evidence supporting that interpretation.

## 4. Experiment procedure

1. **Prepare the evaluation material.** Select and save the source files, define the required tasks, and write reference answers by checking the original documents. Record their versions so both methods use the same inputs.
2. **Develop and test the pipeline.** Use rs671 and other pilot examples to improve the extraction process. These development examples will not be included in the final unbiased comparison.
3. **Choose new evaluation examples.** Select a manageable set of additional variants or traits before starting the final comparison. Include different document types and both clear and incomplete evidence. Do not choose them based on which ones the pipeline handles best.
4. **Run both methods.** Use the same documents and tasks. Record the order of methods, and keep the pipeline configuration unchanged during the evaluation. Avoid using prepared answers while performing either extraction.
5. **Save the first results.** Keep the manual and pipeline outputs before making any corrections, including failed or incomplete runs.
6. **Review the results.** Check each output against its source, record corrections and missing information, and save the reviewed versions.
7. **Compare the results.** Calculate the measures below for both methods before and after review, and compare the human time required.

If I prepare the reference answers and review the results myself, I will state this limitation in the thesis.

## 5. Evaluation measures

I will use four main measures:

| Measure                 | How it will be evaluated                                                                                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Accuracy**            | Number of required findings recorded correctly, compared with the total number of assigned findings. A finding is correct only when its value **and scientific context** match the source. |
| **Completeness**        | Number of required fields recorded, or correctly marked unavailable, compared with the total number of required fields.                                                                    |
| **Source traceability** | Number of factual findings that include a correct source and a location supporting the finding, compared with the number of findings requiring a citation.                                 |
| **Human effort**        | Minutes spent manually extracting, checking and correcting information. Pipeline processing time will be recorded separately.                                                              |

I will also record **serious errors**, such as using the wrong allele, mixing up study populations, inventing numerical values or presenting a study association as an individual prediction.

All measures will be reported as counts with clear totals (for example, **6 of 8 tasks correct**), not just percentages. If the source genuinely does not contain a requested detail, correctly marking it as unavailable is acceptable. A missing value that _was_ available in the provided files counts as incomplete.

Accuracy, completeness and traceability will be checked on both the **first-pass output** and the **reviewed output**. This will show how much manual correction each approach needs.

## 6. Recording results

A spreadsheet and saved output files are enough for this experiment; no additional database or experiment-management system is required.

For each example, I will record:

- The trait, source files and method used.
- The original extracted result and final reviewed result.
- Correct, missing and incorrect fields, with references to the source documents.
- Corrections made and any unresolved questions.
- Active human time, plus separate automated processing time and retries.

The time used to build the pipeline or prepare reference answers will be recorded separately from the time needed to curate one example. The final evaluation will include unsuccessful attempts, not only successful outputs.

## 7. Limitations and expected outcome

rs671 is already familiar development material, so it cannot by itself show how well the pipeline works on unseen traits. The final evaluation will therefore use additional examples selected in advance. The number will be chosen based on the available thesis time and agreed with the supervisor.

The evaluation will have limitations: a small set of examples, one main reviewer, possible familiarity with the sources, and differences between scientific publications. These limitations will be discussed alongside the results.

The expected outcome is a measured comparison of **extraction quality and human effort**. Even if the assisted method proves faster, the results will not establish that the platform can predict personal health outcomes or that extracted scientific findings can be published without review.
