import json
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[1]
repository_root = backend_root.parent
sys.path.insert(0, str(backend_root))

from app.main import app  # noqa: E402

output_path = repository_root / "contracts" / "openapi.json"
output_path.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"Wrote {output_path}")
