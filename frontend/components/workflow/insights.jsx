"use client";
import { useState } from "react";
import { downloadFile, post } from "@/lib/api";
import { Field, Job, Status, useAction, useApi } from "./common";
import { Empty, PageHeader } from "@/components/ui/studio-ui";
import { humanize } from "@/lib/creator.mjs";
import { PublicYouTubeMetrics, YouTubeMetrics } from "./youtube";

export function Insights({ projectId }) {
  const [scope, setScope] = useState("project"),
    [job, setJob] = useState(null),
    [explanation, setExplanation] = useState(null);
  const data = useApi(
    scope === "project" ? `/projects/${projectId}/insights` : "/me/insights",
  );
  const workflow = useApi(`/projects/${projectId}/workflow`, true);
  const publications = useApi(`/projects/${projectId}/publications`);
  const action = useAction();
  const confirmed =
    publications.data?.filter((p) => p.status === "published") || [];
  const activeJob =
    job ||
    workflow.data?.jobs.find((item) => item.type === "insight_summary")?.id;
  const summary = useApi(activeJob ? `/jobs/${activeJob}` : null, true);
  const insights = data.data;
  const result = explanation || summary.data?.result;
  return (
    <section className="workspace insights-workspace">
      <PageHeader
        title="Learn from what you make."
        description="Production activity and performance insights you can act on."
      />
      <div className="tabs" aria-label="Insights scope">
        {[
          ["project", "This project"],
          ["creator", "All my projects"],
        ].map(([key, label]) => (
          <button
            key={key}
            aria-pressed={scope === key}
            onClick={() => {
              setScope(key);
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <Status query={data} error={action.error} />
      {insights && (
        <>
          <h2>Production</h2>
          <dl className="metrics">
            {Object.entries(insights.production).map(([key, value]) => (
              <div key={key}>
                <dt>{key.replaceAll("_", " ")}</dt>
                <dd data-empty={value === null}>
                  {value === null
                    ? "No data yet"
                    : Number.isInteger(value)
                      ? value
                      : value.toFixed(2)}
                </dd>
              </div>
            ))}
          </dl>
          <h2>Performance</h2>
          {insights.missing_data.map((message) => (
            <p key={message}>{message}</p>
          ))}
          {insights.performance.length > 0 && (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Post</th>
                    <th>Platform</th>
                    <th>Window</th>
                    <th>Views</th>
                    <th>Engagement</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {insights.performance.map((row) => (
                    <tr key={row.snapshot_id}>
                      <td>{row.title || row.publication_id.slice(0, 8)}</td>
                      <td>{row.platform}</td>
                      <td>
                        {row.reporting_window_days} days
                        {row.reporting_basis === "youtube_calendar_days" &&
                          " · YouTube calendar"}
                      </td>
                      <td>{row.views}</td>
                      <td>
                        {row.engagement_rate === null
                          ? "Incomplete counts"
                          : `${(row.engagement_rate * 100).toFixed(2)}%`}
                      </td>
                      <td>{row.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {insights.recommendations.length > 0 && (
            <h2>Recommendations with evidence</h2>
          )}
          {insights.recommendations.map((r) => (
            <div key={r.platform + r.reporting_window_days + r.reporting_basis}>
              <p>{r.message}</p>
              <p className="muted">
                {r.platform} · {r.reporting_window_days}-day window ·{" "}
                {r.sample_size} posts.
                {r.reporting_basis === "youtube_calendar_days" &&
                  " YouTube calendar days."}{" "}
                {r.limitation}
              </p>
              <details>
                <summary>Evidence records</summary>
                <p>{r.evidence_snapshot_ids.join(", ")}</p>
              </details>
            </div>
          ))}
        </>
      )}
      {scope === "project" && (
        <section className="form-section">
          <h2>Explain this project’s results</h2>
          <p className="muted">
            A queued explanation of computed facts—not a prediction or a
            substitute for missing observations.
          </p>
          <button
            disabled={
              action.busy ||
              ["queued", "running"].includes(summary.data?.status)
            }
            onClick={() =>
              action.run(async () => {
                const queued = await post(
                  `/projects/${projectId}/insights/summarize`,
                  {},
                  true,
                );
                setJob(queued.id);
                setExplanation(null);
              })
            }
          >
            Generate evidence-backed explanation
          </button>
          <Job
            id={activeJob}
            pollInterval={1000}
            onDone={(record) => setExplanation(record.result)}
          />
          {result?.summary && (
            <div className="notice">
              <p>{result.summary}</p>
              <ul>
                {result.limitations?.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {result.evidence_snapshot_ids?.length > 0 && (
                <details>
                  <summary>Cited observations</summary>
                  {result.evidence_snapshot_ids.map((id) => {
                    const observation = insights?.performance.find(
                      (item) => item.snapshot_id === id,
                    );
                    return (
                      <p key={id}>
                        {observation
                          ? `${humanize(observation.platform)} · ${observation.reporting_window_days}-day window · ${observation.views} views · ${observation.source}`
                          : id}
                      </p>
                    );
                  })}
                </details>
              )}
              {activeJob && (
                <button
                  className="secondary"
                  disabled={action.busy}
                  onClick={() =>
                    action.run(() =>
                      downloadFile(
                        `/jobs/${activeJob}/insight-report.pdf`,
                        "creatorai-ai-insight-report.pdf",
                      ),
                    )
                  }
                >
                  Download AI report (PDF)
                </button>
              )}
            </div>
          )}
        </section>
      )}
      {scope === "project" && (
        <YouTubeMetrics
          projectId={projectId}
          publications={confirmed.filter(
            (publication) => publication.platform === "youtube",
          )}
        />
      )}
      {scope === "project" && <PublicYouTubeMetrics />}
      <h2>Enter real performance</h2>
      {confirmed.length ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const fields = new FormData(e.currentTarget);
            const optional = (key) =>
              fields.get(key) === "" ? null : Number(fields.get(key));
            action.run(() =>
              post(`/publications/${fields.get("publication")}/performance`, {
                observed_at: new Date(fields.get("observed")).toISOString(),
                reporting_window_days: Number(fields.get("window")),
                views: Number(fields.get("views")),
                likes: optional("likes"),
                comments: optional("comments"),
                shares: optional("shares"),
                retention: optional("retention"),
                source: fields.get("source"),
              }),
            );
          }}
        >
          <Field label="Published post">
            <select name="publication">
              {confirmed.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.platform} · {p.supporting_copy.title}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Observation date (local timezone)">
            <input name="observed" type="datetime-local" required />
          </Field>
          <Field label="Reporting window (days since publication)">
            <input
              name="window"
              type="number"
              min="1"
              max="365"
              defaultValue="7"
              required
            />
          </Field>
          <div className="columns">
            {["views", "likes", "comments", "shares"].map((key) => (
              <Field key={key} label={key}>
                <input
                  name={key}
                  type="number"
                  min="0"
                  required={key === "views"}
                />
              </Field>
            ))}
          </div>
          <Field label="Metric source">
            <input
              name="source"
              required
              placeholder="Manually copied from Instagram Insights"
            />
          </Field>
          <Field label="Retention fraction (optional, 0 to 1)">
            <input
              name="retention"
              type="number"
              min="0"
              max="1"
              step="0.001"
            />
          </Field>
          <p>
            Leave unknown counts blank. Engagement is computed only when all
            counts are present.
          </p>
          <button disabled={action.busy}>Save sourced observation</button>
        </form>
      ) : (
        <Empty title="Keep the numbers connected">
          Confirm a publication in Publish before recording its sourced
          performance.
        </Empty>
      )}
    </section>
  );
}
