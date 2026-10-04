# Google Trends in script generation

Open a project's Script screen and expand **Recent trends · optional** in the
generation panel. Choose a region (India by default), then **Find relevant trends**.
An optional focus, such as `cricket`, replaces the saved brief terms for discovery.
Select one topic before generating hooks and a script, or leave all topics unselected.

The backend reads Google's public RSS feed at
`https://trends.google.com/trending/rss?geo=IN`. No API key or extra package is needed.
It caches feeds for up to ten minutes and considers topics published within the
past 48 hours. The RSS feed does not provide a reliable active/ended flag.

Suggestions use shared terms from topic names and related article titles, matched
against the project brief, audience, and saved brand/product context. This is a
simple discovery filter, not a semantic relevance score or proof a topic belongs
in the script. It supports Unicode terms but does not translate between languages.
At most three suggestions are returned. No matches produces an empty result.

## API

`GET /v1/projects/{project_id}/scripts/trends?country=IN&focus=cricket` is owner-scoped.
`focus` is optional and limited to 200 characters; `country` is an uppercase
two-letter region code. The response includes `source`, `country`, `fetched_at`,
`source_url`, `lookback_hours`, and `topics`. Each topic includes its ID, title,
publication time, approximate search traffic, related article links, matched terms,
and the reason for its suggestion.

Pass the returned topic ID to the existing generation endpoint:

```json
{
  "target_duration_seconds": 60,
  "language": "english",
  "trend": {
    "country": "IN",
    "topic_id": "<24-character topic ID from the response>"
  }
}
```

The server resolves the selection against Google data; client-supplied topic text
and URLs are rejected. A disappeared or outdated topic returns `409`, asking the
creator to refresh or clear the selection. Provider failures return `503`. Omit
`trend` to generate normally without making any Google request.

Accepted jobs freeze the selected topic, timestamps, and source links in
`input_snapshot.selected_trend`; generated versions retain that snapshot. Retrying
an accepted submission with the same idempotency key reuses the frozen inputs,
even if Google is unavailable or the feed has changed. Changed inputs conflict.

Hook writing, script writing, AI review, and revision all receive instructions to
use the topic only when it fits the brief and brand requirements. Trend metadata
is optional inspiration. Article titles are not treated as verified current-event
facts or full articles; the integration does not fetch article contents or invent
claims from search traffic. Existing source alignment still checks footage support.

## Verification

`backend/tests/test_google_trends.py` covers XML parsing, Unicode, timestamps,
attribution, unsafe links, caching, network failure, owner access, selection
validation, durable snapshots, idempotency, generation prompts, and fallback
generation without Google. The frontend controls were also checked against the
live RSS feed in the local browser.
