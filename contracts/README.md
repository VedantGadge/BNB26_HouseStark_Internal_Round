# API contracts

`openapi.json` is generated from FastAPI and committed for frontend type generation. `fixtures/` provides stable example payloads for UI development and tests; fixtures are not a substitute for real authorization or provider integration.

Refresh the snapshot after changing a route or Pydantic schema:

```bash
backend/.venv/bin/python backend/scripts/export_openapi.py
```
