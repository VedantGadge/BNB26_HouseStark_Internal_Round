# YouTube performance sync

In a project's Insights page, connect a YouTube channel, confirm the YouTube
publication with its video/Shorts URL in Publish, and click **Sync YouTube metrics**.
This imports views, likes, comments and shares into the same sourced performance
snapshots used by engagement calculations and AI explanations. Sync runs on demand.
Manual entry remains available.

## Server setup

1. In a Google Cloud project, enable **YouTube Data API v3** and **YouTube Analytics
   API**. Configure the OAuth consent screen and add test users if the app is in
   testing mode.
2. Create an OAuth client of type **Web application**. Register the frontend
   callback URL exactly, e.g. `http://localhost:3000/youtube/callback`. Use the same
   hostname and port when opening the frontend: browser session state is scoped
   to that origin.
3. Configure backend secrets:

   ```dotenv
   YOUTUBE_CLIENT_ID=your-google-client-id
   YOUTUBE_CLIENT_SECRET=your-google-client-secret
   YOUTUBE_REDIRECT_URI=http://localhost:3000/youtube/callback
   YOUTUBE_TOKEN_ENCRYPTION_KEY=your-persistent-fernet-key
   ```

   Generate the encryption key once:

   ```bash
   rtk proxy .venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
   ```

   Keep secrets on the backend. Retain the encryption key across restarts;
   replacing it requires creators to reconnect.
4. From `backend`, apply the migration before starting the API:

   ```bash
   rtk proxy .venv/bin/alembic upgrade head
   ```

The integration requests `youtube.readonly` for channel/video identification and
`yt-analytics.readonly` for performance. It does not request publishing access.
Google consent and production verification requirements apply to your OAuth app;
see [Google's web-server OAuth guide](https://developers.google.com/identity/protocols/oauth2/web-server).

### Public Shorts lookup

To look up an already-public YouTube Short without connecting its channel, create
an API key in the same Google Cloud project, restrict it to **YouTube Data API
v3**, and set `YOUTUBE_PUBLIC_API_KEY` on the backend. The lookup returns current
lifetime views, likes, comments, title, channel, publication time and duration.
It also returns public channel views, subscribers (when visible), and video count,
plus available video metadata such as definition, captions and live viewer count.
It deliberately does not return shares, retention, traffic sources, audience data,
or a date-window report: those are not public fields. After a lookup, **Generate
AI insight report** fetches a fresh server-side public snapshot and queues an
evidence-backed explanation. The job stores that snapshot as its immutable
evidence; it remains separate from creator-authorized analytics and does not claim
that one video establishes cause.

## Reporting semantics

The requested window is an upper bound on the number of calendar days starting
with the actual YouTube publication date. Dates use YouTube's Pacific timezone.
Sync excludes today's incomplete day and sums the daily API rows through the last
returned date. When Google returns a shorter report, the snapshot records the
actual window and exact dates in its source label. Empty reports and missing
metrics produce a retryable user-facing error and save no invented zero counts.
Retention is left unknown.

YouTube calendar windows are kept separate from manually entered windows when
selecting latest snapshots and comparing posts. Re-syncing a window adds a new
observation; Insights uses the latest one rather than summing cumulative copies.
See Google's [report query documentation](https://developers.google.com/youtube/analytics/reference/reports/query)
and [date dimensions](https://developers.google.com/youtube/analytics/dimensions).

Each creator has one connected channel. Videos must belong to that channel.
OAuth state expires after ten minutes, is bound to the authenticated creator and
the initiating browser, and is consumed once. Refresh tokens are encrypted in
the database; access tokens are short-lived and never returned to the frontend.
Disconnect removes local credentials and attempts Google token revocation.

## API

- `GET /v1/me/youtube`: configuration/connection status and channel label.
- `POST /v1/me/youtube/authorize` with `project_id`: start Google consent.
- `POST /v1/me/youtube/callback` with `state` and `code`: authenticated exchange.
- `DELETE /v1/me/youtube`: disconnect the channel.
- `POST /v1/publications/{id}/performance/youtube` with
  `reporting_window_days` (1–365, default 7): fetch and save available metrics.
- `POST /v1/youtube/public/metrics` with a public YouTube `url`: retrieve the
  current public lifetime snapshot without connecting a channel.
- `POST /v1/youtube/public/insights` with a public YouTube `url` and an
  `Idempotency-Key`: fetch a fresh public snapshot and queue an AI explanation
  that cites it.
