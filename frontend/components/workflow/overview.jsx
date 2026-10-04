"use client";
import Link from "next/link";
import { patch, post } from "@/lib/api";
import { Field, Job, Status, useAction, useApi } from "./common";
import { ArrowLink, PageHeader } from "@/components/ui/studio-ui";
import { humanize } from "@/lib/creator.mjs";

export function Overview({ projectId }) {
  const root = `/projects/${projectId}`, workflow = useApi(root + "/workflow", true);
  const project = useApi(root), action = useAction();
  const state = workflow.data;
  return <section className="workspace"><PageHeader title={state?.name || "Project overview"} description="A little planning. A better story." action={state&&<span className="badge active">{humanize(state.stage)}</span>}/><Status query={workflow} error={action.error} />
    {state && <><div className="two-pane"><div><h2>Your next step</h2><p>{state.next_action}</p><ArrowLink href={root+(!state.checklist.script_saved?"/script":!state.checklist.assets_ready?"/assets":!state.checklist.editing_complete?"/clips":"/publish")}>Continue creating</ArrowLink>
      <div className="checklist">{Object.entries(state.checklist).map(([key, value]) => <label className="check" key={key}><input type="checkbox" checked={value} disabled={key === "script_saved" || action.busy || state.stage === "published"} onChange={(e) => action.run(() => patch(root + "/workflow", { expected_revision: state.revision, [key]: e.target.checked }))} />{key.replaceAll("_", " ")}</label>)}</div>
      {state.blocking_reasons.map((reason) => <p key={reason}>{reason}</p>)}
      {state.next_stage && state.next_stage !== "published" && <button disabled={action.busy || state.blocking_reasons.length > 0} onClick={() => action.run(() => post(root + "/workflow/transitions", { expected_revision: state.revision, stage: state.next_stage }))}>Move to {state.next_stage}</button>}
      {["review", "approved", "exported"].includes(state.stage) && <button className="secondary" disabled={action.busy} onClick={() => action.run(() => post(root + "/workflow/transitions", { expected_revision: state.revision, stage: "editing" }))}>Request changes</button>}
      <p><Link href={`/projects/${projectId}/publish`}>Prepare exported package and publication →</Link></p>
      </div><aside className="inspector"><h2>The story so far</h2><p>{state.brief}</p><p className="muted">Review: {humanize(state.review_status)}</p><p className="muted">Destinations: {state.target_platforms.join(", ") || "Choose platforms in your brief"}</p><p className="muted">Saved versions and originals stay intact as your workflow moves forward.</p></aside></div>
      <h2>Jobs</h2>{state.jobs.length ? state.jobs.map((j) => <Job key={j.id} id={j.id} />) : <p>No operations queued yet.</p>}
      {project.data && <details><summary>Edit project brief</summary><form onSubmit={(e) => { e.preventDefault(); const fields = new FormData(e.currentTarget); action.run(() => patch(root, {
        name: fields.get("name"), brief: fields.get("brief"), audience: fields.get("audience") || null, tone: fields.get("tone") || null,
      })); }}>
        <Field label="Project name"><input name="name" defaultValue={project.data.name} required /></Field>
        <Field label="Brief"><textarea name="brief" defaultValue={project.data.brief} required /></Field>
        <Field label="Audience"><input name="audience" defaultValue={project.data.audience || ""} /></Field>
        <Field label="Tone"><input name="tone" defaultValue={project.data.tone || ""} /></Field><button disabled={action.busy}>Save project details</button>
      </form></details>}
    </>}
  </section>;
}
