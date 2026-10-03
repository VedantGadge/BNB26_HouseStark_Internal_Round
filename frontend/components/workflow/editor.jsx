"use client";
import { useEffect, useState } from "react";
import { post } from "@/lib/api";
import { Field, Job, Media, Status, useAction, useApi } from "./common";

export function remapTrim(recipe, start, end) {
  const delta = start - recipe.source_start_ms, duration = end - start;
  const remap = (item) => ({ ...item, start_ms: Math.max(0, item.start_ms - delta),
    end_ms: Math.min(duration, item.end_ms - delta) });
  return { ...recipe, source_start_ms: start, source_end_ms: end,
    captions: recipe.captions.map(remap).filter((c) => c.end_ms > c.start_ms),
    emphasis_zooms: recipe.emphasis_zooms.map(remap).filter((z) => z.end_ms > z.start_ms),
    title: recipe.title && (() => { const title = remap(recipe.title); return title.end_ms > title.start_ms ? title : null; })() };
}

export function Editor({ projectId, clipId }) {
  const clip = useApi(`/clips/${clipId}`);
  const workflow = useApi(`/projects/${projectId}/workflow`, true);
  const exports = useApi(`/projects/${projectId}/exports`, true);
  const action = useAction();
  const [recipe, setRecipe] = useState(null), [job, setJob] = useState(null), [preview, setPreview] = useState(null);
  const [loadedVersion, setLoadedVersion] = useState("");
  const latest = clip.data?.versions[0];
  useEffect(() => { if (latest) { setRecipe(structuredClone(latest.recipe)); setLoadedVersion(latest.id); } }, [latest?.id]);
  function change(key, value) { setRecipe((r) => ({ ...r, [key]: value })); }
  const reviewJob = workflow.data?.jobs.find((j) => j.type === "clip_generation" && j.status === "waiting_review");
  return <section className="workspace"><h1>Clip editor</h1><Status query={clip} error={action.error} />
    {clip.data && <><h2>{clip.data.candidate.hook}</h2><Media assetId={clip.data.candidate.asset_id} seek={(recipe?.source_start_ms || 0) / 1000} />
      <p className="muted">Source playback. Rendered previews below show the saved captions, crop, and styling.</p>
      {!latest && <button disabled={action.busy} onClick={() => action.run(() => post(`/clip-candidates/${clipId}/edit-versions`, {}))}>Create assisted edit recipe</button>}
    </>}
    {recipe && <><form onSubmit={(e) => { e.preventDefault(); action.run(() => post(`/clip-candidates/${clipId}/edit-versions`, { base_version_id: latest.id, recipe })); }}>
      <h2>Saved version {latest.revision}</h2>
      <Field label="Load earlier recipe"><select value={loadedVersion} onChange={(e) => { const version = clip.data.versions.find((v) => v.id === e.target.value); setLoadedVersion(version.id); setRecipe(structuredClone(version.recipe)); }}><option value={latest.id}>Current version</option>{clip.data.versions.slice(1).map((v) => <option key={v.id} value={v.id}>Version {v.revision}</option>)}</select></Field>
      <div className="columns"><Field label="Source start (seconds)"><input type="number" min="0" step="0.1" value={recipe.source_start_ms / 1000} onChange={(e) => setRecipe((r) => remapTrim(r, Math.round(Number(e.target.value) * 1000), r.source_end_ms))} /></Field>
      <Field label="Source end (seconds)"><input type="number" min="2" step="0.1" value={recipe.source_end_ms / 1000} onChange={(e) => setRecipe((r) => remapTrim(r, r.source_start_ms, Math.round(Number(e.target.value) * 1000)))} /></Field></div>
      <div className="columns"><Field label="Crop horizontal position"><input type="range" min="0" max="1" step="0.01" value={recipe.crop.center_x} onChange={(e) => change("crop", { ...recipe.crop, center_x: Number(e.target.value) })} /></Field>
      <Field label="Crop vertical position"><input type="range" min="0" max="1" step="0.01" value={recipe.crop.center_y} onChange={(e) => change("crop", { ...recipe.crop, center_y: Number(e.target.value) })} /></Field></div>
      <label className="check"><input type="checkbox" checked={recipe.captions_enabled} onChange={(e) => change("captions_enabled", e.target.checked)} />Captions enabled</label>
      <Field label="Caption style"><select value={recipe.caption_style} onChange={(e) => change("caption_style", e.target.value)}>{["clean", "bold", "bold_highlight"].map((s) => <option key={s}>{s}</option>)}</select></Field>
      {recipe.captions.map((c, i) => <Field label={`Caption ${i + 1} · ${(c.start_ms / 1000).toFixed(1)}–${(c.end_ms / 1000).toFixed(1)}s`} key={i}><textarea value={c.text} maxLength={240} onChange={(e) => change("captions", recipe.captions.map((item, index) => index === i ? { ...item, text: e.target.value } : item))} /></Field>)}
      {recipe.title && <Field label="Opening title"><input value={recipe.title.text} maxLength={140} onChange={(e) => change("title", { ...recipe.title, text: e.target.value })} /></Field>}
      <button disabled={action.busy}>Save edit version</button><button type="button" className="secondary" onClick={() => { setRecipe(structuredClone(latest.recipe)); setLoadedVersion(latest.id); }}>Revert unsaved changes</button>
    </form>
    {reviewJob && <button disabled={action.busy} onClick={() => action.run(() => post(`/jobs/${reviewJob.id}/review`, { edit_version_id: latest.id }))}>Submit saved edit for review completion</button>}
    <h2>Export saved version {latest.revision}</h2>
    <form onSubmit={(e) => { e.preventDefault(); const fields = new FormData(e.currentTarget); action.run(async () => { const queued = await post(`/clips/${clipId}/exports`, {
      edit_version_id: latest.id, preset: fields.get("preset"), platform: fields.get("platform"), fit: fields.get("fit"),
      title: fields.get("title"), caption: fields.get("caption"), hashtags: String(fields.get("hashtags") || "").split(/\s+/).filter(Boolean),
    }, true); setJob(queued.id); }); }}>
      <div className="columns"><Field label="Aspect ratio"><select name="preset"><option value="vertical">Vertical · 9:16</option><option value="square">Square · 1:1</option><option value="landscape">Landscape · 16:9</option></select></Field>
      <Field label="Platform"><select name="platform">{["instagram", "tiktok", "youtube"].map((p) => <option key={p}>{p}</option>)}</select></Field>
      <Field label="Framing"><select name="fit"><option value="crop">Crop</option><option value="pad">Pad</option></select></Field></div>
      <Field label="Platform title"><input name="title" defaultValue={clip.data.candidate.hook.slice(0, 160)} required maxLength={160} /></Field>
      <Field label="Platform caption"><textarea name="caption" required maxLength={2000} defaultValue={clip.data.candidate.transcript_text} /></Field>
      <Field label="Hashtags (space separated)"><input name="hashtags" /></Field><button disabled={action.busy}>Queue export</button>
    </form><Job id={job} onDone={(result) => setPreview(result.result.export_id)} /></>}
    <h2>Authoritative renders</h2>{exports.data?.filter((r) => r.edit_version_id === latest?.id && r.processing_status === "completed").map((r) => <button key={r.id} className="secondary" onClick={() => setPreview(r.id)}>{r.preset_name} · {r.width}×{r.height}</button>)}
    {preview && <Media renderId={preview} />}
  </section>;
}
