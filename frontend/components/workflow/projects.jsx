"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { post } from "@/lib/api";
import { Field, Status, useAction, useApi } from "./common";

export function Projects() {
  const projects = useApi("/projects");
  const action = useAction();
  const router = useRouter();
  const [token, setToken] = useState("");
  return <main className="workspace projects"><h1>Your projects</h1>
    <details><summary>Creator session</summary><p>Use your provider's access token. Local demo mode uses the backend's demo account.</p>
      <Field label="Access token"><input type="password" value={token} autoComplete="off" onChange={(e) => setToken(e.target.value)} /></Field>
      <button onClick={() => { token.trim() ? sessionStorage.setItem("creatorai-token", token.trim()) : sessionStorage.removeItem("creatorai-token"); projects.refetch(); }}>Use session</button>
    </details>
    <Status query={projects} error={action.error} />
    <div className="rows">{projects.data?.map((project) => <Link key={project.id} className="row" href={`/projects/${project.id}`}><strong>{project.name}</strong><span>{project.workflow_stage}</span></Link>)}
      {projects.data?.length === 0 && <p>No projects yet. Start with your content idea.</p>}</div>
    <h2>New project</h2>
    <form onSubmit={(e) => { e.preventDefault(); const fields = new FormData(e.currentTarget);
      action.run(async () => { const project = await post("/projects", {
        name: fields.get("name"), brief: fields.get("brief"), audience: fields.get("audience") || null,
        tone: fields.get("tone") || null, target_platforms: fields.getAll("platform"),
      }); router.push(`/projects/${project.id}`); }); }}>
      <Field label="Project name"><input name="name" required maxLength={120} /></Field>
      <Field label="Content idea / brief"><textarea name="brief" required maxLength={8000} /></Field>
      <div className="columns"><Field label="Audience"><input name="audience" /></Field><Field label="Tone"><input name="tone" /></Field></div>
      <fieldset><legend>Platforms</legend>{["instagram", "tiktok", "youtube"].map((p) => <label key={p} className="check"><input type="checkbox" name="platform" value={p} defaultChecked={p === "instagram"} />{p}</label>)}</fieldset>
      <button disabled={action.busy}>Create project</button>
    </form>
  </main>;
}

