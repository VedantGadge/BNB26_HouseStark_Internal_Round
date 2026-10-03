"use client";
import { useEffect, useState } from "react";
import { post } from "@/lib/api";
import { Field, Job, Status, useAction, useApi } from "./common";

export function Script({ projectId }) {
  const root = `/projects/${projectId}/scripts`;
  const versions = useApi(root + "/versions");
  const [draft, setDraft] = useState(null);
  const [job, setJob] = useState(null);
  const action = useAction();
  const latest = versions.data?.[0];
  useEffect(() => { if (latest) setDraft(structuredClone(latest.content)); }, [latest?.id]);
  function change(key, value) { setDraft((d) => ({ ...d, [key]: value })); }
  return <section className="workspace"><h1>Script & hooks</h1><Status query={versions} error={action.error} />
    <form onSubmit={(e) => { e.preventDefault(); const fields = new FormData(e.currentTarget); action.run(async () => {
      const queued = await post(root + "/generate", { target_duration_seconds: Number(fields.get("duration")),
        language: fields.get("language"), use_style_profile: false }, true); setJob(queued.id);
    }); }}>
      <div className="columns"><Field label="Target duration (seconds)"><input type="number" name="duration" min="15" max="300" defaultValue="60" /></Field>
      <Field label="Language"><select name="language"><option value="english">English</option><option value="hindi">Hindi</option><option value="hinglish">Hinglish</option></select></Field></div>
      <button disabled={action.busy}>Generate hooks and script</button>
    </form>
    <Job id={job} onDone={() => versions.refetch()} />
    {draft ? <form onSubmit={(e) => { e.preventDefault(); action.run(() => post(root + "/versions", {
      base_version: latest.version, content: draft, acknowledged_warning_ids: latest.warning_ids,
    })); }}>
      <h2>Version {latest.version}</h2>
      <Field label="Version history"><select defaultValue={latest.id} onChange={(e) => { const version = versions.data.find((v) => v.id === e.target.value); setDraft(structuredClone(version.content)); }}>
        {versions.data.map((v) => <option key={v.id} value={v.id}>Version {v.version} · {v.origin}</option>)}</select></Field>
      <h2>Hook alternatives</h2>
      {draft.hooks.map((hook, index) => <div key={hook.id} className="hook">
        <label className="check"><input type="radio" name="selected-hook" checked={draft.selected_hook_id === hook.id} onChange={() => change("selected_hook_id", hook.id)} />Use this hook</label>
        <textarea aria-label={`Hook ${index + 1}`} value={hook.text} onChange={(e) => change("hooks", draft.hooks.map((h, i) => i === index ? { ...h, text: e.target.value } : h))} />
      </div>)}
      {draft.sections.map((section, index) => <Field key={section.id} label={section.heading}><textarea value={section.text} onChange={(e) => change("sections", draft.sections.map((s, i) => i === index ? { ...s, text: e.target.value } : s))} /></Field>)}
      {["title", "description", "call_to_action"].map((key) => <Field key={key} label={key.replaceAll("_", " ")}><textarea value={draft[key]} onChange={(e) => change(key, e.target.value)} /></Field>)}
      <h2>Production notes</h2><ul>{draft.production_notes.map((note, i) => <li key={i}>{note}</li>)}</ul>
      {latest.requirement_checks.map((check) => <p key={check.requirement_id}>{check.status}: {check.message || check.requirement_id}</p>)}
      <button disabled={action.busy}>Save script version</button><button type="button" className="secondary" onClick={() => setDraft(structuredClone(latest.content))}>Revert unsaved changes</button>
    </form> : <p>Generate a script from your project brief to get started.</p>}
  </section>;
}

