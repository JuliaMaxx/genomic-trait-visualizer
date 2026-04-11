import io
from typing import Any

import pytest
from fastapi import UploadFile

from backend.services.dna_service import (
    PARSERS,
    _process_dna_file_sync,
)

# ------------------------
# Helpers
# ------------------------


class DummyResult:
    def __init__(self, variants: Any) -> None:
        self.variants = variants


def make_upload_file(content: str) -> UploadFile:
    return UploadFile(
        filename="test.txt",
        file=io.BytesIO(content.encode("utf-8")),
    )


# ------------------------
# Tests
# ------------------------


def test_uses_correct_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, bool] = {}

    def fake_parser(lines: Any) -> DummyResult:
        called["used"] = True
        return DummyResult([])

    monkeypatch.setitem(PARSERS, "23andme", fake_parser)
    monkeypatch.setattr(
        "backend.services.dna_service.detect_format",
        lambda _: "23andme",
    )

    file = make_upload_file("rs123\t1\t1000\tAA\n")

    _process_dna_file_sync(file)

    assert called.get("used") is True


def test_unknown_format_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.services.dna_service.detect_format",
        lambda _: "unknown",
    )

    file = make_upload_file("some random content")

    with pytest.raises(ValueError):
        _process_dna_file_sync(file)


def test_stream_integrity_no_loss_or_duplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_lines = ["a\n", "b\n", "c\n"]

    def fake_parser(stream: Any) -> DummyResult:
        # Collect exactly what parser receives
        return DummyResult(list(stream))

    monkeypatch.setitem(PARSERS, "23andme", fake_parser)
    monkeypatch.setattr(
        "backend.services.dna_service.detect_format",
        lambda _: "23andme",
    )

    file = make_upload_file("".join(input_lines))

    result = _process_dna_file_sync(file)

    assert result == ["a", "b", "c"]
