# Stage 5 — Finding scientific sources and preparing trait proposals

## 1. What I wanted to achieve

Before Stage 5, I could create a trait dossier manually and then review and publish it using the tools from Stages 2–4. The problem was that collecting scientific information for each new trait took a lot of manual work.

In Stage 5, I added a small **semi-automatic research workflow**. I enter a trait name, the program searches supported scientific databases, saves the responses, and prepares a draft dossier for review.

The important distinction is that **the program suggests information; it does not approve scientific claims or generate personal genetic predictions**. A person still has to inspect the evidence, correct the drafts, and make the final decisions.

The workflow is:

```text
Trait name
    ↓
Search GWAS Catalog and Europe PMC
    ↓
Save the original API responses
    ↓
Extract reported values and flag unclear information
    ↓
Create a draft dossier and explanations
    ↓
Human review (Stage 3)
    ↓
Build, approve and publish (Stage 4)
```

I reused the existing dossier, review and publication code instead of building another system. There is no new database, frontend or AI model in this stage.

### Main files

| File | Purpose |
| --- | --- |
| `backend/models/research.py` | Models for research requests, downloaded records and proposed values |
| `backend/services/trait_curation/research_sources.py` | Searches the APIs and saves their responses |
| `backend/services/trait_curation/research_extract.py` | Extracts fields and checks whether values can be normalized safely |
| `backend/services/trait_curation/research.py` | Builds the dossier, drafts explanations, and supports offline replay |
| `backend/services/trait_curation/cli.py` | Provides the `research`, `replay` and `finalize` commands |
| `curation/sources.json` | Lists supported sources and a few search synonyms |
| `backend/tests/unit/test_stage5_research.py` | Tests research, extraction and review handoff |
| `backend/tests/unit/test_stage5_finalize.py` | Tests finalization and publication safeguards |

## 2. Where the information comes from

I use two scientific services:

- **[GWAS Catalog](https://www.ebi.ac.uk/gwas/rest/api/v2/docs)** provides structured information about published genetic associations and their studies.
- **[Europe PMC](https://europepmc.org/RestfulWebService)** finds publications by searching titles and abstracts. It also lets me look up publications linked to GWAS studies by their PubMed ID (PMID).

The search starts with the trait name and any user-provided or configured synonyms. For example, a search for lactose digestion may also try *lactose tolerance test*. A synonym is only an extra search term: it is not proof that two scientific traits are identical.

GWAS Catalog may return ontology terms (standardized trait names). The program selects only sufficiently matching terms for association searches. Other candidates are kept in the review files, but are not automatically treated as equivalent traits.

I deliberately limit each search. The implementation supports at most five combined search terms, three ontology matches per term, three selected ontology IDs, and 1–10 distinct GWAS associations. Independent Europe PMC results are also bounded by the requested association limit. It checks the first pages rather than trying to download all results.

**Why these limits?** Stage 5 is a demonstrator, not a full literature-review system. Small searches make the process easier to inspect, reproduce and test. They also avoid placing unnecessary load on the public APIs.

The program avoids duplicate requests where possible, keeps the reasons a result was found, and records failed requests. API calls are sequential, with a 30-second timeout, a 2 MB response-size limit, and no automatic retries. An empty search is a valid outcome; the program does not invent evidence to fill the gap.

## 3. What gets saved

I save the downloaded responses **before** extracting scientific information. This means I can return to the original values if a proposed interpretation looks wrong.

A research run contains:

- `run.json` — search terms, API requests, response locations, timestamps, file hashes and errors.
- `responses/` — the original saved API response bodies.

The generated proposal contains:

| File | What it contains |
| --- | --- |
| `raw-extraction.json` | The values extracted from source records, with their locations and warnings |
| `normalized.json` | The original reported values alongside cautious proposed values |
| `dossier.json` | A Stage 2 dossier with pending evidence, claims and text drafts |
| `drafting.json` | Which statements and evidence were used to produce each draft |
| `review.md` | A concise review organized by finding, with essential reported values, uncertainties and source references |
| `acquisition.json` | A list of source documents used by the publication workflow |
| `processing.json` | Processing versions, hashes and other run metadata |

The files serve different purposes: the downloaded response is the original input; the extracted and normalized files show what the program did with it; and the dossier is what the reviewer can correct.

The CLI shows the trait, counts of retrieved source records, evidence proposals and draft explanations, important warnings, file locations and the next review action. Source counts refer to records included in the dossier, rather than API requests. Detailed retrieval and extraction warnings are in `review.md` and the saved JSON files.

The report shows shared study and publication context and repeated limitations once. It keeps reported measurements, conflicting values and unresolved information visible, with source IDs and locations for checking them. Full draft explanations remain in `dossier.json`; exact field locations, transformations, hashes and provenance remain in the structured files. The shorter report does not change extraction, review, approval or publication behavior. The CLI uses action labels such as **Review proposed information** and **Ready to publish** instead of stage numbers; readiness still requires the existing publication checks and explicit approval.

### Replay and file integrity

Each retained response has a **SHA-256 hash**, which is a checksum of its bytes. When I replay a saved run, the program checks these hashes before using the responses. If a response was changed or is missing, replay fails instead of silently using different scientific inputs.

`replay` uses saved files, so it does not need an internet connection. With the same inputs and code version, the six main proposal files are reproduced byte for byte. The processing timestamp is kept separately because it naturally changes between runs.

The dossier also records the original acquisition-run hash. During publication, this connects the reviewed proposal to the saved research inputs. A local `acquisition-link.json` tells the candidate where to find those inputs for later checks; it is not included in the published release.

The frozen lactose example in `curation/examples/stage5-lactose-search/` keeps its original **v1** outputs as a historical record. More recent output uses extractor **v10** and drafting templates **v8**. To generate current proposals, replay the saved acquisition into a new directory rather than overwriting the frozen example.

These hashes help detect accidental or unauthorized changes inside the workflow. They do **not** prove that a published scientific paper is correct or that an external source is authentic.

## 4. How the scientific information is handled

This was the part where I chose to be deliberately conservative. A database response may contain useful information, but that does not mean I can directly turn it into a genotype prediction.

The extractor keeps reported phenotypes, variant identifiers, alleles, study details, statistical values, ancestry and sample descriptions, and source references. Each proposed field points back to a location in the saved response.

The main rules are:

- **Do not guess missing values.** For example, `?` is not converted into a known effect allele, and an unfamiliar historical marker name is not guessed to be an rsID.
- **Check conflicting allele representations.** If two fields disagree about a marker, the proposed marker and allele are withheld. If they agree on the marker but disagree on the allele, the allele is withheld. The original values and a warning remain available.
- **Do not simplify complex associations into one marker.** Haplotype and interaction records are preserved for review, not turned into single-variant rules.
- **Keep scientific qualifiers.** This includes source descriptions, background traits (`bg_efo_traits`), interaction flags (`gxe`, `gxg`), sample details and ancestry. These describe the study context, not personal or causal conclusions.
- **Check linked studies and publications.** If an association and its linked study give different PMIDs, the study's information is not added to the association's explanation as though the link had been verified.
- **Keep very small p-values accurately.** When a value such as `3e-400` is supplied through mantissa and exponent fields, the draft uses scientific notation rather than incorrectly displaying `0.0` because of floating-point underflow.
- **Do not invent biological interpretations.** Mapped genes are not automatically called causal genes, coordinates are not assigned an unknown genome build, and reported statistical estimates are not used as prediction scores.

Unclear information remains marked as unresolved. If one association record is malformed, the program records a warning and can still process valid neighboring records.

**Why handle data this way?** The project is intended to explain how results are supported by evidence. Keeping uncertainty visible is more useful than producing a confident-looking answer from incomplete research data.

## 5. Draft explanations and human review

I used **simple, fixed templates** for the first version of explanation assistance. The program can draft a trait description, simple and technical summaries, scientific context and short marker-related explanations.

I did not add an LLM. The templates are easier to reproduce and make it clearer which scientific fields produced each sentence. They also avoid making conclusions based on an abstract that the program has not scientifically interpreted. I retain publication metadata and small API responses with attribution, but I do not download full papers or copy abstracts into the generated explanations.

The drafts describe what the sources *report*. They do not say that the trait has been proven for an individual, and they do not create result-specific predictions. Publications found only through a literature search remain bibliographic candidates until a reviewer establishes their relevance.

Every generated evidence item, claim and explanation starts **pending review**. I use the existing Stage 3 tools to inspect, revise, approve or reject the dossier. If evidence changes, dependent approvals become outdated and must be checked again.

A reviewer may add a justified interpretation and independently prepared expected cases. Stage 5 itself does not make those choices. This separation is important: **finding scientific information is not the same as validating it**.

For the individual review commands and editing workflow, see [Stage 3](stage3-review.md).

## 6. Trying Stage 5 locally

Run these commands from the repository root in PowerShell. Use new output directories, because existing research runs are not overwritten.

### A. Replay the saved example (no internet required)

```powershell
$python = '.\venv\Scripts\python.exe'
$cli = 'backend.services.trait_curation.cli'

& $python -m $cli replay curation/examples/stage5-lactose-search curation/runs/lactose-replay
Get-Content curation/runs/lactose-replay/review.md -Encoding UTF8

& $python -m $cli init curation/runs/lactose-replay/dossier.json curation/reviews/lactose-replay
& $python -m $cli status curation/reviews/lactose-replay
```

This creates a draft dossier and a review workspace. It does **not** approve the science or publish a trait.

The original frozen acquisition was collected on **10 November 2026**. It includes two GWAS associations, one linked study and one publication: **four pending evidence records** in total. Some markers and effect alleles remain unresolved. The original example has not received scientific approval.

### B. Make a new API search (internet required)

```powershell
& $python -m $cli research 'Lactose Digestion Ability' curation/runs/lactose-live --limit 2
Get-Content curation/runs/lactose-live/proposal/review.md -Encoding UTF8
```

Results may differ from the saved example because online databases change. Check the generated report and source files rather than assuming any particular association will appear.

To correct or reject proposals, use the existing `inspect`, `revise` and `decide` commands documented in Stage 3. The original acquisition remains unchanged.

### C. Finalize only after a real review

The `finalize` command combines the existing Stage 4 steps: check approvals and independent expected cases, build a candidate, show its preview and fingerprint, request explicit `publish` confirmation, then approve and publish the exact candidate.

For a **fictional, fully reviewed test workspace**, the command looks like this:

```powershell
& $python -m $cli finalize curation/reviews/synthetic-stage4-practice curation/candidates/synthetic-finalize-practice --release-id synthetic-finalize-practice-v1 --cases curation/examples/synthetic-stage4-cases.json --reviewer synthetic-demo --rationale 'Reviewed the fictional preview and expected cases.' --releases data/releases
```

This example requires the fictional workspace to have been created and approved first; see [Stage 4](stage4-publication.md).

For a Stage 5-generated dossier, also provide `--acquisition` pointing to that proposal's `acquisition.json`, together with its own independently authored cases. The system checks acquisition integrity during build, release approval and publication. The separate Stage 4 commands have the same checks, so using them cannot skip source verification. Manual Stage 4 dossiers still work without a Stage 5 acquisition.

Publication verifies the approved files. A published release can be checked later even if the original acquisition directory is no longer available.

## 7. Testing

The tests are offline: they use frozen responses or fictional API responses rather than relying on live services.

`test_stage5_research.py` checks searches, saved data, replay, scientific normalization, explanations and review handoff. `test_stage5_finalize.py` checks approvals, independent cases, source-integrity failures and both publication paths.

The main checks can be run with:

```powershell
& $python -B -m pytest backend/tests/unit/test_stage5_research.py backend/tests/unit/test_stage5_finalize.py -q -p no:cacheprovider -p no:cov
& $python -B -m pytest backend/tests -q -p no:cacheprovider -p no:cov
& $python -B -m ruff check --no-cache backend
& $python -B -m mypy --config-file mypy.ini backend
& $python -B -m black --check backend
```

Verification on **12 November 2026**: **121 Stage 5 tests passed; 722 backend tests passed and 32 historical tests skipped**. Ruff, mypy and Black passed. The historical skips require an older project checkout. Test counts should be updated after future test changes; the commands above are the way to check the current version.

## 8. Limitations and next steps

Stage 5 is a **working research assistant for a small set of supported APIs**, not an automatic scientific curator.

It does not perform a systematic literature review, read arbitrary full papers, resolve all genetic variant formats, decide which results are scientifically true, or generate clinical probabilities. Search results may be incomplete or empty. Human review is still necessary.

The frozen lactose run demonstrates that research data can be collected and transformed into reviewable proposals. It is not proof that the generated claims are scientifically valid, and it is not a measurement of time saved compared with manual curation. That comparison belongs to the later thesis evaluation.

Stages 6–9 will address DNA representation matching, using approved releases in the application, user-facing presentation and a controlled comparison of manual versus assisted curation.

### Why I kept this design simple

I chose a small number of trusted APIs, bounded searches, saved raw responses, conservative extraction, and human approval because each decision makes the workflow easier to understand, test and justify. More advanced automation would be possible later, but it would also make scientific errors harder to trace in this first version.
