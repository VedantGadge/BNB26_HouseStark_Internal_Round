# Real LLM validation — 2026-10-04

Tested the actual ScriptCreationService LangGraph workflow with OpenRouter using
the configured `liquid/lfm-2.5-2.6b:free` model. No fake provider responses were
used. Both cases used synthetic briefs and dedicated local PostgreSQL schemas,
which were removed afterward. No production records were modified.

| Case | Result | Calls | Elapsed | Input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- |
| Organic creator script | Completed; reviewer approved | 3 | 34.767 s | 1,342 | 3,404 |
| Brand and closing signature | Completed after one revision | 4 | 42.837 s | 3,456 | 6,737 |

The two live tests passed in 78.60 seconds. They verified structured responses,
the three/four-call limit, final-version persistence, immutable input snapshots,
mandatory requirement checks and invalidation of previous creator approval.
The second case naturally exercised the revision branch: its real AI reviewer
rejected the draft's timing estimates. The required brand name and closing
signature were satisfied; approved claims remained flagged for human review.

## Content quality findings

Functional passing does not establish editorial quality:

- The organic draft has 123 section words, but all section duration estimates
  are null. Its production notes claim approximately 45 seconds; this is not
  verified by actual audio timing.
- The brand reviewer identified 49 seconds in the first draft, but recommended
  changing estimates rather than trimming spoken content. The revised section
  estimates still add to 47 seconds, while production notes claim 45 seconds.
- The final brand CTA invents a **free** template; the brief only approves that
  PlanPilot provides a weekly content planning template. Hooks/description also
  introduce growth promises. The reviewer did not catch these unsupported claims.
- The signature exists in the closing section as required, but also appears in
  hooks. Its presence check does not enforce exclusive placement.

These findings support keeping creator review. A follow-up improvement should
check duration against actual spoken text, strengthen approved-claim review,
and validate the revised draft's subjective issues. This run does not compare
quality against the original two-call flow, and it does not measure audio runtime
or billed dollar cost. Token totals are provider-reported and can include
reasoning tokens.

## Reproduce

From `backend/`, with the local PostgreSQL test container running and the configured
OpenRouter credentials available:

```bash
rtk proxy env CREATORAI_QA_LIVE=1 \
  CREATORAI_TEST_DATABASE_URL=postgresql://creatorai_test:local_test_only@127.0.0.1:55432/creatorai_test \
  CREATORAI_LIVE_REPORT_DIR=../output/qa \
  .venv/bin/pytest -q -s tests/test_script_live.py
```

Live tests are skipped unless `CREATORAI_QA_LIVE=1` is explicitly set. Each case
permits at most four real requests. Local JSON reports contain stage responses,
latency, token counts, checks and final scripts:

- `output/qa/script-live-organic.json`
- `output/qa/script-live-brand_and_signature.json`
