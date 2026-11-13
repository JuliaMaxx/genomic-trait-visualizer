# Stage 7 — Backend integration

## 1. What I wanted to achieve

Stage 4 introduced the publication and offline interpretation of reviewed traits. Stage 6 added DNA ingestion and compatibility matching. In Stage 7, I connected these components to FastAPI so the application can analyze uploaded DNA using explicitly selected, verified trait releases.

Each published release still contains one trait. The application can load several releases together, so adding another reviewed trait does not require changing the publication system or interpretation engine.

## 2. What I reused

I reused Stage 4's `verify_release()` and `evaluate()` functions, its published trait models, and Stage 6's `ingest_dna()` and `match_observation()`. Stage 3 review decisions and final release approval remain part of the existing publication workflow.

Most of the new integration code is in `backend/services/active_traits.py` and `backend/models/reviewed_api.py`, with smaller changes to FastAPI startup and routes. The old scoring engine remains for historical tests but is no longer used by the public analysis routes.

## 3. How active releases work

I select the releases using a small JSON file. The `WHOAMI_ACTIVE_RELEASE_SET` environment variable points to this file:

```json
{
  "releases": [
    "releases/first-reviewed-v1",
    "releases/second-reviewed-v1"
  ]
}
```

These are example paths, not releases included in the repository. Relative paths are resolved from the configuration file's directory; absolute paths also work.

When FastAPI starts, it verifies every selected release using Stage 4, loads its trait, and rejects duplicate trait IDs. Missing configuration, unpublished releases, changed files, or failed verification prevent startup. Loading does not modify publication files.

Each trait response includes a `release_id` and `manifest_sha256`, which identify the individual publication and its manifest. Every response also includes a `release_set_id` identifying the complete selected collection. This identity stays the same when identical releases are loaded in a different order or location, but changes when the collection or a release version changes.

**There is no default active release set.** The repository contains fictional test publications but does not automatically use them as scientific content. Normal use requires genuinely reviewed and published traits. Technical verification confirms recorded approval and file integrity; it does not prove a scientific conclusion is correct.

To change the active set, update the configuration and restart the application.

## 4. How the API works

The existing routes now use only the selected, verified traits:

- `GET /traits/` lists active traits and their release identities.
- `GET /traits/{trait_id}` returns the published trait, including sources, evidence, claims, limitations, and explanations.
- `POST /analyze/` accepts an uploaded DNA file and returns one result per active trait.
- `POST /traits/{trait_id}/evaluate` accepts a DNA file and returns the selected trait with its analysis. An unknown or inactive trait returns HTTP 404.

For analysis, the backend reads the uploaded DNA using Stage 6, matches observations against each trait's published requirements, and then calls Stage 4's `evaluate()`.

At present, uploads must follow the verified Stage 6 subset: identified 23andMe four-column text, with explicit GRCh37 (Build 37) and forward-strand metadata, and diploid autosomal SNVs. Unsupported formats return HTTP 415 with an explanation.

When an observation is missing, malformed, conflicting, or incompatible, its result is **unavailable**, not an inferred trait result. The API includes the Stage 4 unavailable reason and a more specific Stage 6 observation status and diagnostic. In this integration, the Stage 4 reason for a withheld observation is `missing_genotype`. Missing information is never treated as zero allele copies. A problem with one trait does not prevent another trait from being evaluated.

Educational traits return published educational text without making a genotype-based conclusion. All result explanations come from the reviewed release; the backend does not invent scores, confidence percentages, or likelihood labels.

Search and rsID browsing are temporarily withheld so they cannot show content from the old, unselected catalog: `/search/` and `/rsids/` return empty lists, and `/rsids/{rsid}` returns HTTP 404. Restoring useful browsing belongs to the frontend and browsing work in Stage 8.

## 5. A small fictional example

The integration tests load two separately published **fictional** traits that refer to the same invented marker, `rs12345678`, at chromosome 1, position 101.

| Fictional trait | Published requirement | Result for a Build 37 `GA` upload |
| --- | --- | --- |
| `synthetic_stage7_allele` | GRCh37 (Build 37) | `evaluated`, `copies: 1`, observation `usable` |
| `synthetic_allele` | GRCh38 (Build 38) | `unavailable`, `copies: null`, observation `incompatible` |

Both results have the same `release_set_id` but retain their individual `release_id` values. This demonstrates correct software behavior and release selection, **not** a scientifically validated personal trait prediction.

## 6. How to run it

### Run the Stage 7 demonstration tests

From the repository root in PowerShell:

```powershell
.\venv\Scripts\python.exe -m pytest backend/tests/integration/stage7 -q
```

The tests create and verify fictional publications in temporary directories. You do not need to create an active release configuration to run them.

### Start the API with selected releases

For a manual run, first create your own `active.json` file containing paths to **existing, verified published releases** in the format shown in Section 3. Set the environment variable to that file, then start the server:

```powershell
$env:WHOAMI_ACTIVE_RELEASE_SET = (Resolve-Path "path/to/active.json").Path
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In another terminal, you can inspect the catalog and upload a fictional supported sample:

```powershell
curl.exe http://127.0.0.1:8000/traits/
curl.exe -F "file=@backend/tests/dna_samples/stage6/23andme_build37.txt" http://127.0.0.1:8000/analyze/
```

The repository does not currently provide genuinely approved scientific releases for normal use. Use the automated tests for a repeatable fictional demonstration; do not configure fictional test releases as real scientific content.

## 7. Testing and API contracts

Stage 7 is tested through real FastAPI HTTP requests using fictional published traits. Tests cover startup verification, loading multiple releases, stable release identities, incompatible DNA observations, unavailable results, educational content, and rejection of legacy or unsupported behavior.

**Reported verification on 12 November 2026:** 35 Stage 7 tests and 246 focused tests passed. Ruff, mypy, Black, isort, and OpenAPI/TypeScript contract consistency checks also passed.

The complete backend run reported **759 passed, 32 skipped, and 65 failed**. The 65 failures were traced to an existing Stage 5 archive inconsistency: five saved API response files disagree with hashes recorded in `run.json`. The scientific files and recorded hashes were left unchanged. This problem is separate from Stage 7 and still needs resolving before final thesis verification.

Useful commands from the repository root:

```powershell
$python = '.\venv\Scripts\python.exe'
& $python -m pytest backend/tests/integration/stage7 -q
& $python -m pytest backend/tests -q
& $python -m ruff check backend
& $python -m mypy --config-file mypy.ini backend
& $python -m black --check backend
```

FastAPI generates the OpenAPI schema, and `openapi-typescript` generates frontend API types. The Stage 7 contract checks compared generated files with the saved artifacts. The existing React pages have not yet been migrated, so full frontend TypeScript checking remains unsuccessful until Stage 8.

## 8. Limitations and next steps

Stage 7 completes the **backend integration**, not the finished user interface. Stage 8 must update React to display reviewed results, explanations, source references, limitations, and unavailable states instead of legacy confidence and likelihood labels. It should also restore browsing using only active reviewed traits and avoid mixing results from different release sets.

The verified DNA input subset remains limited to Stage 6's supported 23andMe representation. There is no automatic discovery of releases, live reloading, new approval process, or calculation of clinical probabilities. Stage 9 will address the remaining curator workflow and thesis evaluation.
