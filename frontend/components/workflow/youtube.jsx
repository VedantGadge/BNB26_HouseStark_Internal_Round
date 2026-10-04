"use client";

import Link from "next/link";
import { useState } from "react";
import { apiFetch, downloadFile, post } from "@/lib/api";
import { Field, Job, Status, useAction, useApi } from "./common";

function displayDuration(value) {
  const match = /^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/.exec(value || "");
  if (!match) return "Unavailable";
  const [, hours, minutes, seconds] = match;
  return [
    hours && `${hours}h`,
    minutes && `${minutes}m`,
    seconds && `${seconds}s`,
  ]
    .filter(Boolean)
    .join(" ");
}

export function YouTubeMetrics({ projectId, publications }) {
  const account = useApi("/me/youtube");
  const action = useAction();
  const [synced, setSynced] = useState(null);

  return (
    <section className="form-section">
      <h2>YouTube performance</h2>
      <p className="muted">
        Connect your channel to import views, likes, comments and shares for
        your published videos and Shorts.
      </p>
      <Status query={account} error={action.error} />
      {account.data && (
        <>
          {account.data.connected && (
            <p>Connected to {account.data.channel_title}.</p>
          )}
          {!account.data.configured && (
            <p>
              YouTube connection is currently unavailable. You can enter metrics
              below.
            </p>
          )}
          <div className="actions">
            <button
              disabled={action.busy || !account.data.configured}
              onClick={() =>
                action.run(async () => {
                  const result = await post("/me/youtube/authorize", {
                    project_id: projectId,
                  });
                  sessionStorage.setItem(
                    "creatorai-youtube-state",
                    result.state,
                  );
                  window.location.assign(result.authorization_url);
                })
              }
            >
              {account.data.connected ? "Reconnect YouTube" : "Connect YouTube"}
            </button>
            {account.data.connected && (
              <button
                className="secondary"
                disabled={action.busy}
                onClick={() =>
                  action.run(async () => {
                    await apiFetch("/me/youtube", { method: "DELETE" });
                    setSynced(null);
                  })
                }
              >
                Disconnect YouTube
              </button>
            )}
          </div>
          {publications.length ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                const fields = new FormData(event.currentTarget);
                setSynced(null);
                action.run(async () => {
                  const result = await post(
                    `/publications/${fields.get("publication")}/performance/youtube`,
                    { reporting_window_days: Number(fields.get("window")) },
                  );
                  setSynced(result);
                });
              }}
            >
              <Field label="Published YouTube video">
                <select name="publication">
                  {publications.map((publication) => (
                    <option key={publication.id} value={publication.id}>
                      {publication.supporting_copy.title || "YouTube video"}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Import up to this many days since publication">
                <input
                  name="window"
                  type="number"
                  min="1"
                  max="365"
                  defaultValue="7"
                  required
                />
              </Field>
              <p className="muted">
                Save the video’s YouTube URL in Publish first. Reports use
                YouTube’s Pacific calendar days and may lag behind live counts.
                The saved window reflects the data available when you sync.
              </p>
              <button
                disabled={
                  action.busy ||
                  !account.data.connected ||
                  !account.data.configured
                }
              >
                {action.busy ? "Working…" : "Sync YouTube metrics"}
              </button>
            </form>
          ) : (
            <p>
              <Link href={`/projects/${projectId}/publish`}>
                Confirm a YouTube publication
              </Link>{" "}
              to sync its performance.
            </p>
          )}
          {synced && (
            <p role="status">
              Imported {synced.views} views, {synced.likes} likes,{" "}
              {synced.comments} comments and {synced.shares} shares across{" "}
              {synced.reporting_window_days} YouTube calendar days.
            </p>
          )}
        </>
      )}
    </section>
  );
}

export function PublicYouTubeMetrics() {
  const action = useAction();
  const [metrics, setMetrics] = useState(null);
  const [job, setJob] = useState(null);
  const [report, setReport] = useState(null);

  return (
    <section className="form-section">
      <h2>Look up a public YouTube Short</h2>
      <p className="muted">
        Current public lifetime counts. This does not require channel access.
      </p>
      <Status error={action.error} />
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const url = new FormData(event.currentTarget).get("url");
          setMetrics(null);
          setJob(null);
          setReport(null);
          action.run(async () => {
            const result = await post("/youtube/public/metrics", { url });
            setMetrics(result);
          });
        }}
      >
        <Field label="Public YouTube video or Shorts URL">
          <input
            name="url"
            type="url"
            placeholder="https://youtube.com/shorts/..."
            required
          />
        </Field>
        <button disabled={action.busy}>
          {action.busy ? "Looking up…" : "Get public metrics"}
        </button>
      </form>
      {metrics && (
        <div className="notice" role="status">
          <p>
            <strong>{metrics.title}</strong> · {metrics.channel_title}
          </p>
          <dl className="metrics">
            <div>
              <dt>Views</dt>
              <dd>{metrics.views?.toLocaleString() ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Likes</dt>
              <dd>{metrics.likes?.toLocaleString() ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Comments</dt>
              <dd>{metrics.comments?.toLocaleString() ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Engagement</dt>
              <dd>
                {metrics.engagement_rate === null
                  ? "Unavailable"
                  : `${(metrics.engagement_rate * 100).toFixed(2)}%`}
              </dd>
            </div>
            <div>
              <dt>Channel subscribers</dt>
              <dd>
                {metrics.channel_statistics?.subscribers_hidden
                  ? "Hidden"
                  : (metrics.channel_statistics?.subscribers?.toLocaleString() ??
                    "Unavailable")}
              </dd>
            </div>
            <div>
              <dt>Channel views</dt>
              <dd>
                {metrics.channel_statistics?.views?.toLocaleString() ??
                  "Unavailable"}
              </dd>
            </div>
            <div>
              <dt>Channel videos</dt>
              <dd>
                {metrics.channel_statistics?.videos?.toLocaleString() ??
                  "Unavailable"}
              </dd>
            </div>
            {metrics.metadata?.concurrent_viewers !== null && (
              <div>
                <dt>Live viewers</dt>
                <dd>{metrics.metadata.concurrent_viewers.toLocaleString()}</dd>
              </div>
            )}
          </dl>
          <p className="muted">
            Published {new Date(metrics.published_at).toLocaleDateString()} ·
            duration {displayDuration(metrics.duration)} ·{" "}
            {metrics.metadata?.definition || ""}
            {metrics.metadata?.caption_available ? " · captions" : ""}
          </p>
          <p className="muted">
            Public API data includes lifetime video and channel counts. Shares,
            retention, traffic sources, audience demographics and historical
            daily data require the channel owner’s connection.
          </p>
          <button
            disabled={action.busy}
            onClick={() =>
              action.run(async () => {
                const queued = await post(
                  "/youtube/public/insights",
                  { url: metrics.canonical_url },
                  true,
                );
                setJob(queued.id);
                setReport(null);
              })
            }
          >
            Generate AI insight report
          </button>
          <Job
            id={job}
            pollInterval={1000}
            onDone={(record) => setReport(record.result)}
          />
          {report?.summary && (
            <div className="notice">
              <p>{report.summary}</p>
              <ul>
                {report.limitations?.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <button
                className="secondary"
                disabled={action.busy}
                onClick={() =>
                  action.run(() =>
                    downloadFile(
                      `/jobs/${job}/insight-report.pdf`,
                      "creatorai-youtube-insight-report.pdf",
                    ),
                  )
                }
              >
                Download AI report (PDF)
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
