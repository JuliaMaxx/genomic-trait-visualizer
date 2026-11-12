"""Bounded acquisition from two documented APIs; saved responses are replay inputs."""

import json
import re
import time
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.models.research import (
    ResearchRequest,
    ResearchRun,
    ResponseKind,
    SavedResponse,
    SourceId,
    SourceRegistry,
)
from backend.services.trait_curation.compiler import sha256
from backend.services.trait_curation.workflow import write_json_new

REGISTRY = Path(__file__).resolve().parents[3] / "curation/sources.json"
MAX_BYTES = 2_000_000


def search_terms(request: ResearchRequest, registry: SourceRegistry) -> list[str]:
    trait_name = " ".join(request.trait_name.split())
    terms = [trait_name, *request.synonyms]
    terms.extend(registry.synonyms.get(trait_name.casefold(), []))
    # Keep user spelling, but collapse case/whitespace duplicates.
    distinct: dict[str, str] = {}
    for term in terms:
        clean = " ".join(term.split())
        distinct.setdefault(clean.casefold(), clean)
    if len(distinct) > 5:
        raise ValueError(
            "At most five combined search terms are supported; remove a --synonym "
            "or reduce registry synonyms. Combined terms: "
            + "; ".join(distinct.values())
        )
    return list(distinct.values())


def collection(data: dict[str, Any], name: str) -> list[Any]:
    """v2 omits _embedded for an empty page; other shapes are parsing errors."""
    page = data.get("page")
    if "page" in data and not isinstance(page, dict):
        raise ValueError("Unsupported GWAS response: page must be an object")
    if "_embedded" not in data and page is not None and page.get("totalElements") == 0:
        return []
    embedded = data.get("_embedded")
    if not isinstance(embedded, dict):
        raise ValueError("Unsupported GWAS response: _embedded must be an object")
    rows = embedded.get(name)
    if not isinstance(rows, list):
        raise ValueError(f"Unsupported GWAS response: expected _embedded.{name}")
    return rows


def association_identity(row: dict[str, Any], trait_id: str | None) -> str:
    identifier = str(row.get("association_id", ""))
    if not identifier.isdigit():
        raise ValueError("missing/invalid association identity")
    traits = row.get("efo_traits")
    if not isinstance(traits, list) or any(not isinstance(t, dict) for t in traits):
        raise ValueError(f"Association {identifier}: malformed efo_traits")
    if trait_id not in [t.get("efo_id") for t in traits]:
        raise ValueError(f"Association {identifier}: ontology mismatch")
    return identifier


class RetrievalError(OSError):
    """Carry an available HTTP status when reading the body fails."""

    def __init__(self, error: OSError | HTTPException, status_code: int) -> None:
        super().__init__(f"{type(error).__name__}: {error}")
        self.status_code = status_code


def fetch(url: str) -> tuple[int, bytes]:
    """No credentials, retries, full-text access or arbitrary link traversal."""
    time.sleep(0.1)  # At most 10 requests/second, below GWAS's documented 15.
    request = Request(
        url, headers={"Accept": "application/json", "User-Agent": "whoami-stage5/1"}
    )
    try:
        response = urlopen(request, timeout=30)
    except HTTPError as exc:
        response = exc  # Preserve error bodies, including rate-limit failures.
    with response:
        try:
            return response.status, response.read(MAX_BYTES + 1)
        except (OSError, HTTPException) as exc:
            # A partial body is not retained as a scientific source document.
            raise RetrievalError(exc, response.status) from exc


def read_response(root: Path, response: SavedResponse) -> dict[str, Any]:
    if response.path is None or response.sha256 is None:
        raise ValueError(f"No saved bytes for {response.document_id}")
    path = (root / response.path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Response path escapes the research run")
    raw = path.read_bytes()
    if sha256(raw) != response.sha256:
        raise ValueError(f"Source hash mismatch: {response.document_id}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object from the scientific API")
    return data


def acquire(
    request: ResearchRequest, destination: Path, registry_path: Path = REGISTRY
) -> ResearchRun:
    registry = SourceRegistry.model_validate_json(registry_path.read_bytes())
    sources = {source.source_id: source for source in registry.sources}
    if set(sources) != {"gwas_catalog", "europe_pmc"} or len(registry.sources) != 2:
        raise ValueError(
            "The registry must contain the two supported APIs exactly once"
        )
    terms = search_terms(request, registry)
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "responses").mkdir()
    responses: list[SavedResponse] = []
    warnings = [
        "First pages only; a bounded discovery sample, not a literature review.",
        "Search matches and ontology synonyms require human relevance review.",
    ]

    def get(
        source: SourceId,
        kind: ResponseKind,
        route: str,
        parameters: dict[str, str],
        reason: str,
    ) -> dict[str, Any] | None:
        url = sources[source].base_url.rstrip("/") + "/" + route
        if parameters:
            url += "?" + urlencode(parameters)
        record = SavedResponse(
            document_id=f"response-{len(responses) + 1:03d}",
            source_id=source,
            kind=kind,
            url=url,
            parameters=parameters,
            query_reason=reason,
            retrieved_at=datetime.now(timezone.utc),
            elapsed_seconds=0,
        )
        tick = time.perf_counter()
        data = None
        try:
            record.status_code, raw = fetch(url)
            record.path = f"responses/{record.document_id}.json"
            record.sha256 = sha256(raw)
            with (destination / record.path).open("xb") as stream:
                stream.write(raw)
            if record.status_code != 200:
                raise ValueError(f"HTTP {record.status_code}; no automatic retry")
            if len(raw) > MAX_BYTES:
                raise ValueError(
                    "Response exceeded 2 MB; retained prefix, not extracted"
                )
            data = read_response(destination, record)
        except (OSError, HTTPException, ValueError) as exc:
            if isinstance(exc, RetrievalError):
                record.status_code = exc.status_code
            record.error = f"{type(exc).__name__}: {exc}"
            warnings.append(f"{record.document_id} {kind}: {exc}")
        record.elapsed_seconds = round(time.perf_counter() - tick, 6)
        responses.append(record)
        return data

    traits: dict[str, list[str]] = {}
    for term in terms:
        data = get(
            "gwas_catalog",
            "traits",
            "efo-traits",
            {"efo_trait": term, "page": "0", "size": "3"},
            f"Trait search term: {term}",
        )
        if data is None:
            continue
        try:
            rows = collection(data, "efo_traits")
            if not rows:
                warnings.append(f"No ontology matches for {term!r}.")
            for row in rows[:3]:
                if not isinstance(row, dict):
                    warnings.append(f"Skipped malformed ontology match: {row!r}")
                    continue
                identifier, label = row.get("efo_id"), row.get("efo_trait")
                if (
                    not isinstance(identifier, str)
                    or not re.fullmatch(r"[A-Za-z]+_\d+", identifier)
                    or not isinstance(label, str)
                ):
                    warnings.append(f"Skipped unexpected ontology match: {row!r}")
                    continue
                if term.casefold() not in label.casefold():
                    warnings.append(
                        f"Ontology candidate {identifier} ({label!r}) returned for "
                        f"{term!r}: not selected automatically; review relevance."
                    )
                    continue
                traits.setdefault(identifier, []).append(f"{term} -> {label}")
        except (ValueError, TypeError, AttributeError) as exc:
            warnings.append(f"Trait response could not be parsed: {exc}")

    associations: dict[str, dict[str, Any]] = {}
    for trait_id, matches in list(traits.items())[:3]:
        if len(associations) >= request.limit:
            break
        data = get(
            "gwas_catalog",
            "associations",
            "associations",
            {
                "efo_id": trait_id,
                "show_child_trait": "false",
                "page": "0",
                "size": str(request.limit - len(associations)),
            },
            "Potential relevance only: " + "; ".join(matches),
        )
        if data is None:
            continue
        try:
            rows = collection(data, "associations")
        except (ValueError, TypeError, AttributeError) as exc:
            warnings.append(f"Association response could not be parsed: {exc}")
            continue
        for index, row in enumerate(rows):
            try:
                if not isinstance(row, dict):
                    raise ValueError("expected an association object")
                identifier = association_identity(row, trait_id)
                if len(associations) < request.limit:
                    associations.setdefault(identifier, row)
            except ValueError as exc:
                warnings.append(f"Association record {index} skipped: {exc}")
    if not associations:
        warnings.append(
            "No suitable association records retrieved; no evidence invented."
        )
    studies = sorted(
        {str(row.get("accession_id", "")) for row in associations.values()}
    )
    for study in studies:
        if re.fullmatch(r"GCST\d+", study):
            get(
                "gwas_catalog",
                "study",
                f"studies/{study}",
                {},
                f"Study {study} linked by discovered association(s)",
            )
    pmids = sorted({str(row.get("pubmed_id", "")) for row in associations.values()})
    for pmid in pmids:
        if pmid.isdigit():
            get(
                "europe_pmc",
                "publication",
                "search",
                {
                    "query": f"EXT_ID:{pmid} AND SRC:MED",
                    "format": "json",
                    "resultType": "core",
                    "pageSize": "1",
                },
                f"PMID {pmid} linked by discovered association(s)",
            )
    # Independent discovery always runs, even when GWAS found no associations.
    for term in terms:
        quoted = term.replace("\\", "\\\\").replace('"', '\\"')
        get(
            "europe_pmc",
            "literature",
            "search",
            {
                "query": f'TITLE_ABS:"{quoted}" AND SRC:MED',
                "format": "json",
                "resultType": "core",
                "pageSize": str(request.limit),
            },
            f"Bibliographic candidates only; title/abstract search term: {term}",
        )
    run = ResearchRun(
        request=request,
        registry=registry,
        search_terms=terms,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        acquisition_seconds=round(time.perf_counter() - started, 6),
        responses=responses,
        warnings=warnings,
    )
    write_json_new(destination / "run.json", run.model_dump(mode="json"))
    return run
