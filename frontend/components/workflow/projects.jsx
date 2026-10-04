"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { post } from "@/lib/api";
import { Field, Status, useAction, useApi } from "./common";
import { StudioShell } from "@/components/project-shell/project-shell";
import { Empty, Modal, PageHeader } from "@/components/ui/studio-ui";
import { ArrowRight, Plus } from "@phosphor-icons/react";
import { humanize } from "@/lib/creator.mjs";

export function Projects() {
  const projects = useApi("/projects");
  const action = useAction();
  const router = useRouter();
  const [search,setSearch]=useState(""),[stage,setStage]=useState("all"),[open,setOpen]=useState(false);
  const visible=projects.data?.filter((p)=>(stage==="all"||p.workflow_stage===stage)&&p.name.toLowerCase().includes(search.toLowerCase()));
  return <StudioShell><section className="workspace projects"><PageHeader title="Your projects" description="From the first idea to the final frame. Keep every story connected." action={<button className="button" onClick={()=>setOpen(true)}><Plus size={18} weight="light"/>New project</button>}/>
    <Status query={projects} error={action.error} />
    <div className="toolbar"><Field label="Find a project"><input type="search" value={search} placeholder="Search project names" onChange={(e)=>setSearch(e.target.value)}/></Field><Field label="Stage"><select value={stage} onChange={(e)=>setStage(e.target.value)}><option value="all">All stages</option>{[...new Set(projects.data?.map((p)=>p.workflow_stage))].map((s)=><option value={s} key={s}>{humanize(s)}</option>)}</select></Field></div>
    <div className="rows">{visible?.map((project) => <Link key={project.id} className="project-row" href={`/projects/${project.id}`}><div><h2>{project.name}</h2><p>{project.brief}</p></div><span className="badge">{humanize(project.workflow_stage)}</span><ArrowRight size={20} weight="light"/></Link>)}
      {visible?.length === 0 && <Empty title={projects.data?.length ? "No matching projects" : "Make room for your next story"} action={<button onClick={()=>setOpen(true)}>Create a project</button>}>{projects.data?.length ? "Try another name or stage." : "Start with your idea. Your scripts, footage, edits and exports will live together."}</Empty>}</div>
    <Modal open={open} onOpenChange={setOpen} title="New project" description="Give your story a name and a clear starting point. You can refine the brief later.">
    <form onSubmit={(e) => { e.preventDefault(); const fields = new FormData(e.currentTarget);
      action.run(async () => { const project = await post("/projects", {
        name: fields.get("name"), brief: fields.get("brief"), audience: fields.get("audience") || null,
        tone: fields.get("tone") || null, target_platforms: fields.getAll("platform"),
      }); setOpen(false); router.push(`/projects/${project.id}`); }); }}>
      <Field label="Project name"><input name="name" required maxLength={120} /></Field>
      <Field label="Content idea / brief"><textarea name="brief" required maxLength={8000} /></Field>
      <div className="columns"><Field label="Audience"><input name="audience" /></Field><Field label="Tone"><input name="tone" /></Field></div>
      <fieldset><legend>Platforms</legend>{["instagram", "tiktok", "youtube", "linkedin"].map((p) => <label key={p} className="check"><input type="checkbox" name="platform" value={p} defaultChecked={p === "instagram"} />{p}</label>)}</fieldset>
      <button disabled={action.busy}>Create project</button>
      <Status error={action.error}/>
    </form></Modal>
  </section></StudioShell>;
}
