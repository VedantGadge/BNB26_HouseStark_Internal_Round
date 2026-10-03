"use client";
import Link from "next/link";
import { useState } from "react";
import { post } from "@/lib/api";
import { Field, Job, Media, Status, time, useAction, useApi } from "./common";

export function Clips({ projectId }) {
  const assets = useApi(`/projects/${projectId}/assets`);
  const clips = useApi(`/projects/${projectId}/clips`, true);
  const exports = useApi(`/projects/${projectId}/exports`, true);
  const workflow = useApi(`/projects/${projectId}/workflow`, true);
  const action = useAction();
  const [job, setJob] = useState(null);
  const [preview, setPreview] = useState(null);
  return <section className="workspace"><h1>Grounded clip proposals</h1><Status query={clips} error={action.error} />
    <form onSubmit={(e) => { e.preventDefault(); const assetId = new FormData(e.currentTarget).get("asset");
      action.run(async () => { const queued = await post(`/projects/${projectId}/clips/generate`, { asset_id: assetId, max_candidates: 3 }, true); setJob(queued.id); }); }}>
      <Field label="Analyzed source video"><select name="asset" required><option value="">Choose source</option>{assets.data?.filter((a) => a.kind === "video" && a.processing_status === "ready").map((a) => <option key={a.id} value={a.id}>{a.tags.join(", ") || a.id.slice(0, 8)} · {time(a.duration_ms)}</option>)}</select></Field>
      <button disabled={action.busy}>Generate three proposals</button>
    </form>
    <Job id={job} />
    {workflow.data?.jobs.filter((j) => j.type === "clip_generation" && j.id !== job).slice(0, 3).map((j) => <Job key={j.id} id={j.id} />)}
    <div className="rows">{clips.data?.map((clip) => <article key={clip.id} className="clip-row"><h2>{clip.hook}</h2>
      <p>{time(clip.source_start_ms)}–{time(clip.source_end_ms)} · {Math.round(clip.score * 100)}% match confidence</p>
      <p className="muted">Source script version: {clip.script_version_id?.slice(0, 8) || "manual alignment"}</p>
      <p>{clip.transcript_text}</p><p className="muted">Evidence: {clip.reasons.join(", ")}. Ranking is a review heuristic.</p>
      <Link className="button" href={`/projects/${projectId}/clips/${clip.id}`}>Edit this clip</Link>
    </article>)}</div>
    {clips.data?.length === 0 && <p>Analyze a source video and save a script first. Proposals appear here as the worker finishes.</p>}
    <h2>Rendered previews & exports</h2>{exports.data?.filter((r) => r.processing_status === "completed").map((r) => <button key={r.id} className="secondary" onClick={() => setPreview(r.id)}>{r.preset_name} · {r.supporting_copy.title || "Draft preview"}</button>)}
    {preview && <Media renderId={preview} />}
  </section>;
}
