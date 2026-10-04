"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { apiFetch, post } from "@/lib/api";
import { Field, Status, useAction, useApi } from "./common";
import { StudioShell } from "@/components/project-shell/project-shell";
import {
  Empty,
  Modal,
  PageHeader,
  WorkflowRail,
} from "@/components/ui/studio-ui";
import {
  ArrowUpRight,
  Plus,
  Columns,
  List,
  MagnifyingGlass,
  NotePencil,
  FilmStrip,
  Export,
} from "@phosphor-icons/react";
import { humanize } from "@/lib/creator.mjs";
import {
  stageGroup,
  stageGroups,
  nextProjectPath,
  workflowPosition,
} from "@/lib/studio.mjs";

function ProjectCard({ project }) {
  return (
    <Link className="project-card" href={"/projects/" + project.id}>
      <div className="project-card-title">
        <h3>{project.name}</h3>
        <ArrowUpRight size={18} weight="light" aria-hidden="true" />
      </div>
      <p>
        {project.brief ||
          "Open this project to review its brief and continue creating."}
      </p>
      <span className="project-stage">
        <span aria-hidden="true" />
        {humanize(project.workflow_stage)}
      </span>
      <div
        className="project-mini-flow"
        aria-label={"Current stage: " + humanize(project.workflow_stage)}
      >
        {["Brief", "Script", "Footage", "Publish"].map((label, index) => (
          <span
            key={label}
            data-current={index === workflowPosition(project.workflow_stage)}
          >
            {label}
          </span>
        ))}
      </div>
      <div className="project-card-bottom">
        <div className="platform-tags">
          {project.target_platforms?.map((platform) => (
            <span key={platform}>{humanize(platform)}</span>
          ))}
        </div>
        <span>
          Open project <ArrowUpRight size={14} />
        </span>
      </div>
    </Link>
  );
}

export function Projects() {
  const projects = useApi("/projects"),
    action = useAction(),
    router = useRouter();
  const details = useQueries({
    queries: (projects.data || []).map((p) => ({
      queryKey: ["/projects/" + p.id],
      queryFn: () => apiFetch("/projects/" + p.id),
    })),
  });
  const all = (projects.data || []).map((p, index) => ({
    ...p,
    ...details[index]?.data,
  }));
  const [search, setSearch] = useState(""),
    [stage, setStage] = useState("all"),
    [platform, setPlatform] = useState("all"),
    [view, setView] = useState("board"),
    [open, setOpen] = useState(false);
  const visible = all.filter(
    (p) =>
      (stage === "all" || p.workflow_stage === stage) &&
      (platform === "all" || p.target_platforms?.includes(platform)) &&
      (p.name + " " + (p.brief || ""))
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const start = () => setOpen(true);
  return (
    <StudioShell>
      <section className="workspace projects">
        <PageHeader
          title="Your projects"
          description="A place for every idea. A clear path to your next post."
          action={
            <button className="button" onClick={start}>
              <Plus size={18} weight="light" />
              New project
            </button>
          }
        />
        <Status query={projects} error={action.error} />
        <WorkflowRail />
        <div className="project-toolbar">
          <div className="project-search">
            <MagnifyingGlass size={19} weight="light" aria-hidden="true" />
            <input
              aria-label="Find a project"
              type="search"
              value={search}
              placeholder="Search your projects…"
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            aria-label="Stage"
            value={stage}
            onChange={(e) => setStage(e.target.value)}
          >
            <option value="all">All stages</option>
            {[...new Set(all.map((p) => p.workflow_stage))].map((s) => (
              <option key={s} value={s}>
                {humanize(s)}
              </option>
            ))}
          </select>
          <select
            aria-label="Platform filter"
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
          >
            <option value="all">All platforms</option>
            {[...new Set(all.flatMap((p) => p.target_platforms || []))].map(
              (p) => (
                <option key={p} value={p}>
                  {humanize(p)}
                </option>
              ),
            )}
          </select>
          <div className="view-switch" aria-label="Project view">
            {[
              ["board", Columns, "Board"],
              ["list", List, "List"],
            ].map(([key, Icon, label]) => (
              <button
                key={key}
                type="button"
                aria-pressed={view === key}
                onClick={() => setView(key)}
              >
                <Icon size={17} />
                {label}
              </button>
            ))}
          </div>
        </div>
        {projects.data &&
          (visible.length === 0 ? (
            <Empty
              title={
                all.length
                  ? "No matching projects"
                  : "Make room for your next story"
              }
              action={
                <button
                  onClick={
                    all.length
                      ? () => {
                          setSearch("");
                          setStage("all");
                          setPlatform("all");
                        }
                      : start
                  }
                >
                  {all.length ? "Clear filters" : "Create a project"}
                </button>
              }
            >
              {all.length
                ? "Try a different name, stage or platform."
                : "Start with a brief. Your scripts, sources and edits stay connected here."}
            </Empty>
          ) : view === "board" ? (
            <div className="project-board">
              {stageGroups.map((group) => {
                const items = visible.filter(
                    (p) => stageGroup(p.workflow_stage) === group.id,
                  ),
                  Icon =
                    group.id === "ideas"
                      ? NotePencil
                      : group.id === "creating"
                        ? FilmStrip
                        : Export;
                return (
                  <section
                    className="project-lane"
                    key={group.id}
                    aria-label={group.title}
                  >
                    <header>
                      <h2>
                        {group.title}
                        <span>{items.length}</span>
                      </h2>
                      <p>{group.description}</p>
                    </header>
                    <div className="project-lane-items">
                      {items.length ? (
                        items.map((p) => <ProjectCard key={p.id} project={p} />)
                      ) : (
                        <div className="lane-empty">
                          <Icon size={32} weight="light" aria-hidden="true" />
                          <h3>{group.empty}</h3>
                          <p>{group.hint}</p>
                        </div>
                      )}
                    </div>
                  </section>
                );
              })}
            </div>
          ) : (
            <div className="project-list-view">
              {visible.map((p) => (
                <ProjectCard key={p.id} project={p} />
              ))}
            </div>
          ))}
        <section className="studio-start-guide">
          <div>
            <h2>Your next story, one step at a time.</h2>
            <p>A brief, your original footage, and an edit that stays yours.</p>
          </div>
          <button className="secondary" onClick={start}>
            <NotePencil size={19} />
            Start with a brief
          </button>
          {all[0] && (
            <Link
              className="text-link"
              href={nextProjectPath(all[0].id, all[0].workflow_stage)}
            >
              Continue a project <ArrowUpRight size={16} />
            </Link>
          )}
        </section>
        <Modal
          open={open}
          onOpenChange={setOpen}
          title="New project"
          description="Give your story a name and a clear starting point. You can refine the brief later."
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const fields = new FormData(e.currentTarget);
              action.run(async () => {
                const project = await post("/projects", {
                  name: fields.get("name"),
                  brief: fields.get("brief"),
                  audience: fields.get("audience") || null,
                  tone: fields.get("tone") || null,
                  target_platforms: fields.getAll("platform"),
                });
                setOpen(false);
                router.push("/projects/" + project.id);
              });
            }}
          >
            <Field label="Project name">
              <input
                name="name"
                required
                maxLength={120}
                placeholder="What are you creating?"
              />
            </Field>
            <Field label="Content idea / brief">
              <textarea
                name="brief"
                required
                maxLength={8000}
                placeholder="The story, your audience, and what you want them to take away."
              />
            </Field>
            <div className="columns">
              <Field label="Audience">
                <input name="audience" />
              </Field>
              <Field label="Tone">
                <input name="tone" />
              </Field>
            </div>
            <fieldset>
              <legend>Platforms</legend>
              {["instagram", "tiktok", "youtube", "linkedin"].map((p) => (
                <label key={p} className="check">
                  <input
                    type="checkbox"
                    name="platform"
                    value={p}
                    defaultChecked={p === "instagram"}
                  />
                  {humanize(p)}
                </label>
              ))}
            </fieldset>
            <button disabled={action.busy}>Create project</button>
            <Status error={action.error} />
          </form>
        </Modal>
      </section>
    </StudioShell>
  );
}
