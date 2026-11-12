"""Source-specific extraction and conservative normalization, without interpretation."""

import json
import re
from pathlib import Path
from typing import Any

from backend.models.research import (
    Extraction,
    FieldProposal,
    NormalizedRecord,
    RawRecord,
    ResearchRun,
)
from backend.services.trait_curation.research_sources import (
    association_identity,
    collection,
    read_response,
)

ASSOCIATION_FIELDS = (
    "association_id",
    "accession_id",
    "pubmed_id",
    "first_author",
    "reported_trait",
    "efo_traits",
    "bg_efo_traits",
    "snp_allele",
    "snp_effect_allele",
    "mapped_genes",
    "locations",
    "risk_frequency",
    "p_value",
    "pvalue_mantissa",
    "pvalue_exponent",
    "pvalue_description",
    "or_per_copy_num",
    "or_value",
    "beta_num",
    "beta_unit",
    "beta_direction",
    "beta",
    "range",
    "ci_lower",
    "ci_upper",
    "description",
    "multi_snp_haplotype",
    "snp_interaction",
)
STUDY_FIELDS = (
    "accession_id",
    "pubmed_id",
    "disease_trait",
    "bg_efo_traits",
    "initial_sample_size",
    "replication_sample_size",
    "discovery_ancestry",
    "replication_ancestry",
    "gxe",
    "gxg",
    "platforms",
    "genotyping_technologies",
    "terms_of_license",
)
PUBLICATION_FIELDS = (
    "id",
    "source",
    "pmid",
    "pmcid",
    "doi",
    "title",
    "authorString",
    "pubYear",
    "firstPublicationDate",
    "abstractText",
    "isOpenAccess",
    "license",
)


def extract(root: Path, run: ResearchRun) -> Extraction:
    records: dict[str, RawRecord] = {}
    ontology: dict[str, RawRecord] = {}
    conflicts: set[str] = set()
    warnings: list[str] = []
    association_count = 0
    literature_count = 0
    for response in run.responses:
        if response.error:
            continue
        # Missing bytes, invalid JSON and hash failures are acquisition-level errors.
        data = read_response(root, response)
        try:
            if response.kind == "traits":
                rows = collection(data, "efo_traits")[:3]
            elif response.kind == "associations":
                rows = collection(data, "associations")
            elif response.kind == "study":
                rows = [data]
            else:
                rows = data.get("resultList", {}).get("result")
                if not isinstance(rows, list):
                    raise ValueError("expected Europe PMC resultList.result")
                if not rows:
                    warnings.append(f"{response.document_id}: publication not found")
                rows = (
                    rows[:1]
                    if response.kind == "publication"
                    else rows[: run.request.limit]
                )
        except (ValueError, TypeError, AttributeError) as exc:
            warnings.append(
                f"{response.document_id}: response extraction failed: {exc}"
            )
            continue
        for index, row in enumerate(rows):
            try:
                fields: tuple[str, ...]
                if not isinstance(row, dict):
                    raise ValueError("expected a record object")
                if response.kind == "traits":
                    identifier, label = row.get("efo_id"), row.get("efo_trait")
                    if (
                        not isinstance(identifier, str)
                        or not re.fullmatch(r"[A-Za-z]+_\d+", identifier)
                        or not isinstance(label, str)
                    ):
                        raise ValueError("missing/invalid ontology identity or label")
                    term = response.parameters.get("efo_trait", "")
                    selection = (
                        "label matches search text; eligible for bounded retrieval"
                        if term and term.casefold() in label.casefold()
                        else "not selected automatically; "
                        "human relevance review required"
                    )
                    candidate = RawRecord(
                        record_id=f"gwas-ontology-{identifier}",
                        kind="ontology",
                        document_id=response.document_id,
                        locator=f"/_embedded/efo_traits/{index}",
                        found_by=[
                            f"{response.query_reason} "
                            f"[{response.document_id}#/_embedded/efo_traits/{index}]: "
                            f"{selection}"
                        ],
                        fields={
                            key: row[key]
                            for key in ("efo_id", "efo_trait", "uri")
                            if key in row
                        },
                    )
                    if identifier in ontology:
                        ontology[identifier].found_by.extend(candidate.found_by)
                    else:
                        ontology[identifier] = candidate
                    continue
                if response.kind == "associations":
                    identifier = association_identity(
                        row, response.parameters.get("efo_id")
                    )
                    identifier = f"gwas-association-{identifier}"
                    kind, locator, fields = (
                        "association",
                        f"/_embedded/associations/{index}",
                        ASSOCIATION_FIELDS,
                    )
                elif response.kind == "study":
                    study = row.get("accession_id")
                    if not isinstance(study, str) or not response.url.endswith(
                        "/" + study
                    ):
                        raise ValueError(
                            "study identity disagrees with requested accession"
                        )
                    identifier = f"gwas-study-{study}"
                    kind, locator, fields = "study", "", STUDY_FIELDS
                else:
                    pmid = str(row.get("pmid", ""))
                    if (
                        not pmid.isdigit()
                        or row.get("source") != "MED"
                        or str(row.get("id", pmid)) != pmid
                    ):
                        raise ValueError(
                            "publication identity disagrees with MED source/id"
                        )
                    if (
                        response.kind == "publication"
                        and response.parameters.get("query")
                        != f"EXT_ID:{pmid} AND SRC:MED"
                    ):
                        raise ValueError(
                            "publication identity disagrees with requested PMID"
                        )
                    identifier = f"europe-pmc-MED-{pmid}"
                    kind, locator, fields = (
                        "publication",
                        f"/resultList/result/{index}",
                        PUBLICATION_FIELDS,
                    )
                record = RawRecord.model_validate(
                    {
                        "record_id": identifier,
                        "kind": kind,
                        "document_id": response.document_id,
                        "locator": locator,
                        "found_by": [
                            response.query_reason
                            + f" [{response.document_id}#{locator}]"
                        ],
                        "fields": {key: row[key] for key in fields if key in row},
                    }
                )
                if identifier in records:
                    existing = records[identifier]
                    existing.found_by.extend(record.found_by)
                    if existing.fields != record.fields:
                        conflicts.add(identifier)
                        warnings.append(f"Conflicting duplicate {identifier}; withheld")
                elif (
                    response.kind == "literature"
                    and literature_count >= run.request.limit
                ):
                    warnings.append(
                        f"{identifier}: independent literature proposal limit reached; "
                        "snapshot retained"
                    )
                elif kind != "association" or association_count < run.request.limit:
                    records[identifier] = record
                    association_count += kind == "association"
                    literature_count += response.kind == "literature"
            except ValueError as exc:
                warnings.append(
                    f"{response.document_id} record {index}: skipped: {exc}"
                )
    return Extraction(
        records=[record for key, record in records.items() if key not in conflicts],
        ontology_candidates=list(ontology.values()),
        warnings=warnings,
    )


def source_location(record: RawRecord, *tokens: str | int) -> str:
    """Point to an existing value, or its nearest existing parent for an absence."""
    value: Any = record.fields
    pointer = record.locator
    for token in tokens:
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and isinstance(token, int) and token < len(value):
            value = value[token]
        else:
            break
        pointer += "/" + str(token).replace("~", "~0").replace("/", "~1")
    return f"{record.document_id}#{pointer}"


def reported_qualifiers(record: RawRecord) -> list[str]:
    fields: tuple[str, ...]
    if record.kind == "association":
        fields = (
            "p_value",
            "pvalue_mantissa",
            "pvalue_exponent",
            "pvalue_description",
            "description",
            "bg_efo_traits",
            "beta_num",
            "beta_unit",
            "ci_lower",
            "ci_upper",
        )
    elif record.kind == "study":
        fields = (
            "discovery_ancestry",
            "replication_ancestry",
            "gxe",
            "gxg",
            "bg_efo_traits",
        )
    else:
        return []
    notes = []
    for field in fields:
        value = record.fields.get(field)
        if value is not None and value != "" and value != []:
            notes.append(
                f"Source-reported {field} ({source_location(record, field)}): "
                + json.dumps(value, ensure_ascii=False)
            )
    if record.fields.get("bg_efo_traits"):
        notes.append(
            "Background traits describe study context, "
            "not causation or individual applicability. "
            "They do not characterize the general population."
        )
    return notes


def _check_allele_agreement(
    record: RawRecord, fields: list[FieldProposal], unresolved: list[str]
) -> None:
    """Check explicit identities and known alleles without selecting a winner."""
    secondary = record.fields.get("snp_effect_allele")
    if not isinstance(secondary, list):
        return
    proposals = {field.field: field for field in fields}
    rsid, allele = proposals["rsid"], proposals["effect_allele"]
    if rsid.proposed_value is None:
        return  # Primary marker identity is absent, ambiguous or unsupported.
    matches = []
    for entry in secondary:
        if isinstance(entry, str):
            # An rsID can be explicit even if its allele token is unknown or absent.
            # Full matching excludes compound entries containing several markers.
            match = re.fullmatch(
                r"\s*(rs\d+)\s*(?:-\s*([A-Za-z?]*))?\s*", entry, re.IGNORECASE
            )
            if match is not None:
                matches.append(match)
    identity_conflict = any(
        rsid.proposed_value != match[1].lower() for match in matches
    )
    secondary_alleles = {
        (match[2] or "").upper()
        for match in matches
        if (match[2] or "").upper() in ("A", "C", "G", "T")
    }
    allele_conflict = len(secondary_alleles) > 1 or (
        allele.proposed_value is not None
        and any(value != allele.proposed_value for value in secondary_alleles)
    )
    if len(matches) != len(secondary):
        unresolved.append(
            "Some secondary allele notation is unsupported or ambiguous; "
            "original values retained and no secondary value selected. "
            + source_location(record, "snp_effect_allele")
        )
    if not identity_conflict and not allele_conflict:
        return
    disputed = [allele, rsid] if identity_conflict else [allele]
    for proposal in disputed:
        proposal.proposed_value = None
        proposal.transformation = "Withheld: conflicting GWAS allele representations."
    secondary_location = (
        source_location(record, "snp_effect_allele", 0)
        if len(secondary) == 1
        else source_location(record, "snp_effect_allele")
    )
    reported_secondary = secondary[0] if len(secondary) == 1 else secondary
    unresolved.append(
        "Conflicting GWAS allele representations: "
        f"{source_location(record, 'snp_allele')} reports "
        f"{json.dumps(record.fields['snp_allele'], ensure_ascii=False)}; "
        f"{secondary_location} reports "
        f"{json.dumps(reported_secondary, ensure_ascii=False)}. "
        "Normalized effect_allele withheld"
        + (
            " and rsid withheld because marker identities disagree."
            if identity_conflict
            else "; the rsID agrees, but the effect alleles disagree."
        )
    )


def normalize(record: RawRecord) -> NormalizedRecord:
    # GWAS's documented NR frequency and ? effect allele are field-specific.
    # Other sentinel-looking strings are retained for scientific review.
    missing = {"risk_frequency": {"NR"}} if record.kind == "association" else {}
    unresolved = [
        "Relevance to the requested trait and scientific fidelity need review."
    ]
    for key, value in record.fields.items():
        if (
            isinstance(value, str)
            and value.strip() in {"?", "NR", "NA", "-"}
            and value.strip() not in missing.get(key, set())
        ):
            unresolved.append(
                f"Uninterpreted {key} at {source_location(record, key)}: "
                f"{json.dumps(value)}; retained for review."
            )
    fields = [
        FieldProposal(
            field=key,
            reported_value=value,
            proposed_value=(
                None
                if isinstance(value, str) and value.strip() in missing.get(key, set())
                else value
            ),
            source_location=source_location(record, key),
            transformation=(
                "Source missing-value token; proposed as null."
                if isinstance(value, str) and value.strip() in missing.get(key, set())
                else "Copied without scientific reinterpretation."
            ),
        )
        for key, value in record.fields.items()
        if key
        != "abstractText"  # Context retained, no automatic abstract interpretation.
    ]
    if record.kind == "association":
        direction = record.fields.get("beta_direction")
        if direction is not None and direction not in ("increase", "decrease"):
            unresolved.append(
                "Structured effect direction withheld: only explicit increase/decrease "
                "labels are supported; original beta_direction is retained."
            )
        alleles = record.fields.get("snp_allele")
        one_entry = (
            isinstance(alleles, list)
            and len(alleles) == 1
            and isinstance(alleles[0], dict)
        )
        single = (
            one_entry
            and record.fields.get("multi_snp_haplotype") is False
            and record.fields.get("snp_interaction") is False
        )
        allele = alleles[0] if one_entry and isinstance(alleles, list) else {}
        assert isinstance(allele, dict)
        for target, original, pattern in (
            ("rsid", "rs_id", r"rs\d+"),
            ("effect_allele", "effect_allele", r"[ACGT]"),
        ):
            reported = allele.get(original)
            proposed = None
            if single and isinstance(reported, str):
                clean = (
                    reported.strip().lower()
                    if target == "rsid"
                    else reported.strip().upper()
                )
                if re.fullmatch(pattern, clean):
                    proposed = clean
            fields.append(
                FieldProposal(
                    field=target,
                    reported_value=reported,
                    proposed_value=proposed,
                    source_location=(
                        source_location(record, "snp_allele", 0, original)
                        if one_entry
                        else source_location(record, "snp_allele")
                    ),
                    transformation=(
                        "Case/whitespace only for a single reported SNV; "
                        "both association flags must be explicitly false; "
                        "no strand conversion."
                    ),
                )
            )
            if proposed is None:
                unresolved.append(
                    f"{target}: absent, ambiguous or unsupported; left null."
                )
        _check_allele_agreement(record, fields, unresolved)
        traits = record.fields.get("reported_trait")
        phenotype = (
            traits[0]
            if isinstance(traits, list)
            and len(traits) == 1
            and isinstance(traits[0], str)
            else None
        )
        fields.append(
            FieldProposal(
                field="phenotype",
                reported_value=traits,
                proposed_value=phenotype,
                source_location=source_location(record, "reported_trait"),
                transformation="A single reported phenotype; no phenotype recoding.",
            )
        )
        if phenotype is None:
            unresolved.append("Reported phenotype is absent or ambiguous; left null.")
        unresolved.extend(
            [
                "Genome build, allele orientation, comparison/denominator "
                "and personal applicability are unresolved.",
                "Mapped genes may be nearby annotations; "
                "they are not established causal genes.",
                "Reported statistics are evidence, never application "
                "coefficients or personal probabilities.",
                "No genotype interpretation or independent expected cases "
                "have been proposed.",
            ]
        )
        if not single:
            unresolved.append(
                "Multi-variant, haplotype or interaction context: "
                "no single-marker normalization."
            )
    elif record.kind == "ontology":
        unresolved.append(
            "Ontology search candidate only; no phenotype equivalence or scientific "
            "support has been assessed. Selection reasons appear under found_by."
        )
    elif record.kind == "study":
        unresolved.append(
            "Sample descriptions are study-specific, "
            "not evidence of general population applicability."
        )
    else:
        unresolved.append(
            "Abstract is retained as reading context; "
            "its scientific conclusions are not extracted."
        )
    return NormalizedRecord(
        record_id=record.record_id, fields=fields, unresolved=unresolved
    )
