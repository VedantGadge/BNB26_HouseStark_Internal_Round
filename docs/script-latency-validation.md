# Script latency and Gemini comparison — 2026-10-04

The user approved Gemini 3.8 Flash as the app default after reviewing live
results and the reported cost. Default config, local `.env` and `.env.example`
now select `google/gemini-3.8-flash` with paid routing and low thinking. Credentials
were preserved; no deployment or production data changes were performed.

## Real-provider comparison

All cases used the same synthetic organic and brand/signature briefs, structured
outputs, local PostgreSQL persistence and existing creator review controls.
No provider responses were faked. Elapsed time covers the claimed-job service
and persistence, not API queue wait, rendering or video export.

| Configuration | Organic | Brand/signature | Calls | Reported cost per script |
| --- | --- | --- | --- | --- |
| Liquid free; separate hooks/writer | 34.767 s | 42.837 s | 3 / 4 | Free-model route; cost metadata not captured |
| Gemini 3.8 low; separate hooks/writer | 13.620 s | 13.170 s | 3 / 3 | $0.00435825 / $0.005625 |
| Gemini 3.8 low; combined writer | 10.488 s | 8.789 s | 2 / 2 | $0.0033525 / $0.0042195 |

The combined writer generates the three hook alternatives, selects one and
drafts the script in one call. An independent reviewer still runs afterward;
rejection or missing mandatory requirements permits exactly one revision.
Final validation preserves hooks, section IDs and requirement checks before
saving a single final version. The optimized normal path uses two model calls;
the revision path uses three. Each stage allows one provider request.

Compared with the initial measured Liquid runs, optimized Gemini was **69.8%**
faster on the organic brief and **79.5%** faster on the brand brief. Compared with
Gemini before combining the writer, the reduction was **23.0% / 33.3%**. The
initial brand run needed a revision, so the largest improvement combines model
speed with a different review outcome and one fewer writing stage.

## Quality and limits

Gemini passed all schema, brand-name, closing-signature and persistence checks.
In the four Gemini samples, section duration estimates totaled 45 seconds and
the unsupported free-template claim from the earlier Liquid draft did not
appear. Outputs were concise, and signatures stayed in the closing content.
Approved claims still remain marked for creator review.

This is a small smoke comparison, not a statistical benchmark or blind quality
evaluation. Requests were sequential, provider load can vary, and no synthesized
audio was timed. A revision adds another request. Pricing above is the returned
OpenRouter usage cost for these actual runs, not a fixed future cost guarantee.
The catalog marks Gemini thinking as mandatory; the sampled responses reported
zero reasoning tokens, which should not be interpreted as disabling thinking.

Gemini 3.8 is available and supports structured outputs. Its supported thinking
levels are low, medium and high; minimal is unsupported. See
[Google's model specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
and [OpenRouter's model and pricing page](https://openrouter.ai/google/gemini-3.8-flash/providers).

## Reproduce and inspect

Use the explicit live-test command in
[the earlier live validation](script-live-validation.md). The default model is
now Gemini and the test expects two or three requests. Set
`CREATORAI_LIVE_REPORT_DIR=../output/qa/gemini-optimized` to retain fresh reports.
Reports from this comparison are in:

- `output/qa/script-live-*.json`: original Liquid baseline.
- `output/qa/gemini-baseline/script-live-*.json`: original graph with Gemini low.
- `output/qa/gemini-optimized/script-live-*.json`: combined writer with Gemini low.

The live tests remain skipped without explicit `CREATORAI_QA_LIVE=1`. Only new
jobs pick up Gemini; older queues retain their frozen model and routing settings.

## Verification

- Gemini on the original graph: 2 live cases passed in 27.75 seconds.
- Gemini on the combined writer graph: 2 live cases passed in 20.37 seconds.
- Backend regression suite with local PostgreSQL: **118 passed, 2 skipped** in
  11.89 seconds. The skips are the explicitly opt-in real LLM tests already run
  separately above. Coverage includes both real-worker branches on PostgreSQL,
  combined-writer hook counts, immutable revision hooks/IDs, trend snapshots,
  Gemini thinking compatibility, usage metadata and explicit free-only routing.
- Ruff lint passed; formatting check passed for all 118 Python files.
- git diff --check passed.
