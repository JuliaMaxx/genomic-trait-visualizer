import asyncio
import io

from fastapi import UploadFile

from backend.main import app
from backend.routes.analyze_dna import analyze_dna
from backend.routes.search import search
from backend.routes.traits import evaluate_trait as evaluate_trait_route
from backend.routes.traits import read_rsid, read_rsids, read_trait, read_traits


def test_openapi_contains_only_public_request_and_response_models() -> None:
    schema = app.openapi()
    models = schema["components"]["schemas"]

    assert "/traits/{trait_id}" in schema["paths"]
    assert "/traits/{trait_id}/detail" not in schema["paths"]
    assert "TraitAnalysisDetail" in models
    assert "TraitCatalogDetail" in models
    assert "TraitEvaluation" not in models
    assert "ParseResult" not in models


def test_catalog_and_rsid_routes_return_their_declared_models() -> None:
    trait_list = asyncio.run(read_traits())
    trait_detail = asyncio.run(read_trait("lactose_intolerance"))
    rsid_list = asyncio.run(read_rsids())
    rsid_detail = asyncio.run(read_rsid("rs4988235"))

    assert trait_list
    assert trait_list[0].id
    assert trait_detail.rules
    assert trait_detail.result_content.inconclusive
    assert rsid_list
    assert rsid_detail.traits
    assert rsid_detail.sources
    assert "analysis" not in trait_detail.model_dump(mode="json")


def _uploaded_dna() -> UploadFile:
    content = (
        "# 23andMe raw DNA data\nrs4988235 2 136608646 CC\nrs762551 15 74749576 AG\n"
    )
    return UploadFile(filename="sample.txt", file=io.BytesIO(content.encode()))


def test_analysis_routes_serialize_nested_catalog_and_user_data() -> None:
    summary = asyncio.run(analyze_dna(_uploaded_dna()))
    detail = asyncio.run(evaluate_trait_route("lactose_intolerance", _uploaded_dna()))
    encoded_summary = [item.model_dump(mode="json") for item in summary]
    encoded_detail = detail.model_dump(mode="json")

    lactose = next(
        item for item in encoded_summary if item["trait_id"] == "lactose_intolerance"
    )
    assert lactose["rule_statuses"] == [
        {"rsid": "rs4988235", "status": "matched"},
        {"rsid": "rs182549", "status": "missing"},
    ]
    assert set(encoded_detail) == {"trait", "analysis"}
    assert encoded_detail["analysis"]["rules"][0]["status"] == "matched"
    assert encoded_detail["trait"]["rules"][0]["odds_ratio"] == 1.8


def test_search_route_returns_one_list_with_complete_results() -> None:
    response = asyncio.run(search("rs4988235", None, None, 8))
    payload = response.model_dump(mode="json")

    assert payload["query"] == "rs4988235"
    assert payload["results"]
    assert {result["kind"] for result in payload["results"]} <= {"trait", "rsid"}
    assert all(result["subtitle"] for result in payload["results"])
