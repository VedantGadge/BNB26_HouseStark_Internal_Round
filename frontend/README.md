# CreatorAI hackathon frontend

A local, connected SaaS prototype: landing page, projects, script/context/assistant,
private assets and evidence, clips/editing, six platform exports, manual publishing
and sourced insights. The design system is recorded in `../DESIGN.md`.

## Run

Install with `rtk npm ci`, then `rtk npm run dev`. Set
`NEXT_PUBLIC_API_BASE_URL` in `.env.local` to the running backend origin. Frontend
requests use its `/v1` API. An existing local preview is available on port 3000;
the separate verification preview on port 3001 uses an isolated QA backend.

The landing-page photo workflow is explicitly illustrative. It never uploads
demo photos, invents customer metrics, or calls AI services. Open Studio to use
the actual project API. Publication is manual, not automatic social posting.

## Checks

```sh
rtk npm test
rtk npm run test:e2e
rtk npm run build
rtk npm run format:check
```

Browser tests expect a running preview at `http://127.0.0.1:3001`; override with
`CREATORAI_E2E_URL`. Set `CREATORAI_E2E_PROJECT_ID` to an **isolated QA project**
to include connected studio tests. Without it, those checks are explicitly skipped.
They do not modify saved scripts: the recovery test changes and reverts only its
browser-local draft. Chrome must be installed.

During verification, all 20 desktop/mobile browser checks ran, alongside seven
unit checks. Coverage includes light/dark contrast, no horizontal overflow,
three-line maximum mobile hero, demo controls, accordion/carousel, reduced motion,
six studio routes, draft recovery and recording-dialog focus. The real clip
preview was also played and sought against the live isolated backend.

This is a hackathon prototype, not a production-readiness certification. No
production performance audit, hosted deployment, billing or identity-provider
integration is included. Secrets remain in backend environment configuration.
