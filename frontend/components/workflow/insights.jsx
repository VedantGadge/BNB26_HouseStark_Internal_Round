"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { Field, Job, Status, useAction, useApi } from "./common";
import { Empty, PageHeader } from "@/components/ui/studio-ui";
import { humanize } from "@/lib/creator.mjs";
import { YouTubeMetrics } from "./youtube";

const demoPerformance = [
  {
    publication_id: "demo-keep-it-quick",
    project_id: "demo-project",
    snapshot_id: "demo-snapshot-keep-it-quick",
    platform: "instagram",
    reporting_window_days: 7,
    reporting_basis: "creator_demo",
    observed_at: "2026-10-04T12:00:00.000Z",
    source: "Illustrative demo metrics",
    views: 24800,
    likes: 2040,
    comments: 164,
    shares: 322,
    title: "Keep It Quick: Attention Spans Are Gone",
  },
  {
    publication_id: "demo-speak-to-the-scroller",
    project_id: "demo-project",
    snapshot_id: "demo-snapshot-speak-to-the-scroller",
    platform: "instagram",
    reporting_window_days: 7,
    reporting_basis: "creator_demo",
    observed_at: "2026-10-03T12:00:00.000Z",
    source: "Illustrative demo metrics",
    views: 18420,
    likes: 1292,
    comments: 96,
    shares: 214,
    title: "Speak to the Person Scrolling",
  },
  {
    publication_id: "demo-ted-in-one-minute",
    project_id: "demo-project",
    snapshot_id: "demo-snapshot-ted-in-one-minute",
    platform: "instagram",
    reporting_window_days: 7,
    reporting_basis: "creator_demo",
    observed_at: "2026-10-02T12:00:00.000Z",
    source: "Illustrative demo metrics",
    views: 12960,
    likes: 706,
    comments: 51,
    shares: 122,
    title: "A TED Talk in Under a Minute",
  },
].map((record) => ({
  ...record,
  engagement_rate:
    (record.likes + record.comments + record.shares) / record.views,
}));

const demoInsights = {
  project_id: "demo-project",
  scope: "project",
  production: {
    projects_completed: 1,
    source_minutes_processed: 1.35,
    clips_produced: 3,
    exports_completed: 3,
    clips_per_source: 3,
    revision_count: 2,
    median_upload_to_export_seconds: 318,
  },
  performance: demoPerformance,
  recommendations: [
    {
      platform: "instagram",
      reporting_window_days: 7,
      reporting_basis: "creator_demo",
      sample_size: demoPerformance.length,
      evidence_snapshot_ids: demoPerformance.map(
        (record) => record.snapshot_id,
      ),
      message:
        "Review the direct opening and humour in 'Keep It Quick: Attention Spans Are Gone', which has the highest illustrative engagement rate in this sample.",
      limitation:
        "Illustrative demo data only; it does not represent real audience performance or establish causation.",
    },
  ],
  missing_data: [],
};

function demoReportFrom(metrics) {
  const best = metrics.reduce((current, record) =>
    record.engagement_rate > current.engagement_rate ? record : current,
  );
  const averageRate =
    metrics.reduce((sum, record) => sum + record.engagement_rate, 0) /
    metrics.length;
  const totalViews = metrics.reduce((sum, record) => sum + record.views, 0);
  return {
    summary: `Across ${metrics.length} illustrative Instagram posts measured over seven days, '${best.title}' has the highest engagement rate at ${(best.engagement_rate * 100).toFixed(1)}%. The sample totals ${totalViews.toLocaleString()} views, with an average engagement rate of ${(averageRate * 100).toFixed(1)}%. Reuse its direct opening and humour as a testable creative direction.`,
    limitations: [
      "This report is generated from illustrative demo metrics, not real platform analytics.",
      "Three posts are too small a sample to establish cause and effect.",
    ],
    evidence_snapshot_ids: metrics.map((record) => record.snapshot_id),
  };
}

export function Insights({ projectId }) {
  const [scope, setScope] = useState("project"),
    [job, setJob] = useState(null),
    [explanation, setExplanation] = useState(null),
    [demoReport, setDemoReport] = useState(null);
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
  const useDemo = scope === "project" && !data.data?.performance?.length;
  const insights = useDemo ? demoInsights : data.data;
  const result = useDemo ? demoReport : explanation || summary.data?.result;
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
              setDemoReport(null);
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
            {useDemo
              ? "Generate a report from the performance shown above."
              : "A queued explanation of computed facts—not a prediction or a substitute for missing observations."}
          </p>
          <button
            disabled={
              (!useDemo && action.busy) ||
              ["queued", "running"].includes(summary.data?.status)
            }
            onClick={() => {
              if (useDemo) {
                setDemoReport(demoReportFrom(demoInsights.performance));
                return;
              }
              action.run(async () => {
                const queued = await post(
                  `/projects/${projectId}/insights/summarize`,
                  {},
                  true,
                );
                setJob(queued.id);
                setExplanation(null);
                setDemoReport(null);
              });
            }}
          >
            {useDemo
              ? "Generate insights report"
              : "Generate evidence-backed explanation"}
          </button>
          <Job
            id={useDemo ? null : activeJob}
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
