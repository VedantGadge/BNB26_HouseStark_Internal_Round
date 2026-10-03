# CreatorAI

CreatorAI is a creator workspace for moving from an idea and source footage to grounded short-form clips, platform exports, publication tracking, and performance insights.

This repository is the initial scaffold for the approved architecture:

- `frontend/` — Next.js App Router workspace deployed to Vercel.
- `backend/` — FastAPI API and a single persisted-job worker for a Hugging Face Docker Space.
- `contracts/` — checked-in API fixtures and the generated OpenAPI snapshot.

## Local setup

Prerequisites: Node.js 22+, Python 3.12+, and FFmpeg. Docker is optional for the backend container.

```bash
cd creatorai
cp frontend/.env.local.example frontend/.env.local
cp backend/.env.example backend/.env
npm --prefix frontend install
python3 -m venv backend/.venv
backend/.venv/bin/pip install -e './backend[dev]'
```

Run the two services in separate terminals:

```bash
npm --prefix frontend run dev
backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000
```

The starter frontend is at `http://localhost:3000`; the API health check is at `http://localhost:8000/health`.

## Service configuration

Do not commit real secrets. The backend owns Cloudinary credentials, Neon connection strings, model credentials, and JWT verification. The browser receives only `NEXT_PUBLIC_API_BASE_URL` plus narrowly scoped upload-session data returned by the API.

Before a first deployment, select the independent auth provider, create a pinned dependency lockfile, set Cloudinary restricted delivery, configure a Neon database, and set the actual Vercel origin in `CORS_ORIGINS`.

## Contract workflow

The FastAPI application is the OpenAPI source of truth. After changing schemas or routes, install backend dependencies and run:

```bash
backend/.venv/bin/python backend/scripts/export_openapi.py
```

Commit the refreshed `contracts/openapi.json` together with any needed fixtures so the frontend and backend stay aligned.
