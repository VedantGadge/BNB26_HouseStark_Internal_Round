"use client";
import { post } from "@/lib/api";
import { Field, Status, useAction, useApi } from "./common";

export function Insights({ projectId }) {
  const data = useApi(`/projects/${projectId}/insights`);
  const publications = useApi(`/projects/${projectId}/publications`);
  const action = useAction();
  const confirmed = publications.data?.filter((p) => p.status === "published") || [];
  return <section className="workspace"><h1>Creator insights</h1><Status query={data} error={action.error} />
    {data.data && <><h2>Production</h2><dl className="metrics">{Object.entries(data.data.production).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{value === null ? "No data yet" : Number.isInteger(value) ? value : value.toFixed(2)}</dd></div>)}</dl>
      <h2>Performance</h2>{data.data.missing_data.map((message) => <p key={message}>{message}</p>)}
      <div className="table-scroll"><table><thead><tr><th>Post</th><th>Platform</th><th>Window</th><th>Views</th><th>Engagement</th><th>Source</th></tr></thead><tbody>
        {data.data.performance.map((row) => <tr key={row.snapshot_id}><td>{row.title || row.publication_id.slice(0, 8)}</td><td>{row.platform}</td><td>{row.reporting_window_days} days</td><td>{row.views}</td><td>{row.engagement_rate === null ? "Incomplete counts" : `${(row.engagement_rate * 100).toFixed(2)}%`}</td><td>{row.source}</td></tr>)}
      </tbody></table></div>
      <h2>Recommendations with evidence</h2>{data.data.recommendations.map((r) => <div key={r.platform + r.reporting_window_days}><p>{r.message}</p><p className="muted">{r.platform} · {r.reporting_window_days}-day window · {r.sample_size} posts. {r.limitation}</p><details><summary>Evidence records</summary><p>{r.evidence_snapshot_ids.join(", ")}</p></details></div>)}
    </>}
    <h2>Enter real performance</h2>
    {confirmed.length ? <form onSubmit={(e) => { e.preventDefault(); const fields = new FormData(e.currentTarget);
      const optional = (key) => fields.get(key) === "" ? null : Number(fields.get(key));
      action.run(() => post(`/publications/${fields.get("publication")}/performance`, {
        observed_at: new Date(fields.get("observed")).toISOString(), reporting_window_days: Number(fields.get("window")),
        views: Number(fields.get("views")), likes: optional("likes"), comments: optional("comments"), shares: optional("shares"),
        source: fields.get("source"),
      }));
    }}>
      <Field label="Published post"><select name="publication">{confirmed.map((p) => <option key={p.id} value={p.id}>{p.platform} · {p.supporting_copy.title}</option>)}</select></Field>
      <Field label="Observation date (local timezone)"><input name="observed" type="datetime-local" required /></Field>
      <Field label="Reporting window (days since publication)"><input name="window" type="number" min="1" max="365" defaultValue="7" required /></Field>
      <div className="columns">{["views", "likes", "comments", "shares"].map((key) => <Field key={key} label={key}><input name={key} type="number" min="0" required={key === "views"} /></Field>)}</div>
      <Field label="Metric source"><input name="source" required placeholder="Manually copied from Instagram Insights" /></Field>
      <p>Leave unknown counts blank. Engagement is computed only when all counts are present.</p><button disabled={action.busy}>Save sourced observation</button>
    </form> : <p>Confirm a publication in Publish before recording performance.</p>}
  </section>;
}

