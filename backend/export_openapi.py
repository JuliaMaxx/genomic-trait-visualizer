import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app  # noqa: E402

OPENAPI_PATH = PROJECT_ROOT / "frontend" / "openapi.json"


def main() -> None:
    OPENAPI_PATH.write_text(
        json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OPENAPI_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
