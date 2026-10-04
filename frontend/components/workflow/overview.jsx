"use client";
import Link from "next/link";
import { patch, post } from "@/lib/api";
import { Field, Job, Status, useAction, useApi } from "./common";
import {
  ArrowLink,
  PageHeader,
  WorkflowRail,
  PanelHeading,
} from "@/components/ui/studio-ui";
import { ArrowUpRight, CheckCircle, Clock } from "@phosphor-icons/react";
import { humanize } from "@/lib/creator.mjs";
import { workflowNextAction } from "@/lib/studio.mjs";

export function Overview({ projectId }) {
  const root = "/projects/" + projectId,
    workflow = useApi(root + "/workflow", true);
  const project = useApi(root),
    action = useAction(),
    state = workflow.data;
  return (
    <section className="workspace overview-workspace">
      <PageHeader
        title={state?.name || "Project overview"}
        description="Your story, from the first idea to the final post."
        action={
          state && <span className="badge active">{humanize(state.stage)}</span>
        }
      />
      <Status query={workflow} error={action.error} />
      {state && (
        <>
          <WorkflowRail projectId={projectId} stage={state.stage} />
          <div className="two-pane overview-grid">
            <div className="next-action-panel">
              <PanelHeading
                title="Your next step"
                description="Keep the story moving."
              />
              <p className="next-action-copy">{workflowNextAction(state)}</p>
              <ArrowLink
                href={
                  root +
                  (!state.checklist.script_saved
                    ? "/script"
                    : !state.checklist.assets_ready
                      ? "/assets"
                      : !state.checklist.editing_complete
                        ? "/clips"
                        : "/publish")
                }
              >
                Continue creating
              </ArrowLink>
              <div className="workflow-checklist">
                <h3>Production checklist</h3>
                {Object.entries(state.checklist).map(([key, value]) => (
                  <label className="check" key={key}>
                    <input
                      type="checkbox"
                      checked={value}
                      disabled={
                        key === "script_saved" ||
                        action.busy ||
                        state.stage === "published"
                      }
                      onChange={(e) =>
                        action.run(() =>
                          patch(root + "/workflow", {
                            expected_revision: state.revision,
                            [key]: e.target.checked,
                          }),
                        )
                      }
                    />
                    <span>{key.replaceAll("_", " ")}</span>
                    {value && (
                      <CheckCircle
                        size={18}
                        className="success"
                        aria-hidden="true"
                      />
                    )}
                  </label>
                ))}
              </div>
              {state.blocking_reasons.length > 0 && (
                <div className="workflow-blockers">
                  {state.blocking_reasons.map((reason) => (
                    <p key={reason}>{reason}</p>
                  ))}
                </div>
              )}
              <div className="workflow-actions">
                {state.next_stage && state.next_stage !== "published" && (
                  <button
                    disabled={action.busy || state.blocking_reasons.length > 0}
                    onClick={() =>
                      action.run(() =>
                        post(root + "/workflow/transitions", {
                          expected_revision: state.revision,
                          stage: state.next_stage,
                        }),
                      )
                    }
                  >
                    Move to {humanize(state.next_stage)}
                  </button>
                )}
                {["review", "approved", "exported"].includes(state.stage) && (
                  <button
                    className="secondary"
                    disabled={action.busy}
                    onClick={() =>
                      action.run(() =>
                        post(root + "/workflow/transitions", {
                          expected_revision: state.revision,
                          stage: "editing",
                        }),
                      )
                    }
                  >
                    Request changes
                  </button>
                )}
              </div>
              <Link className="text-link" href={root + "/publish"}>
                Prepare your publication <ArrowUpRight size={16} />
              </Link>
            </div>
            <aside className="inspector project-brief">
              <PanelHeading title="The story so far" />
              <p>{state.brief}</p>
              <dl className="brief-facts">
                <div>
                  <dt>Review</dt>
                  <dd>{humanize(state.review_status)}</dd>
                </div>
                <div>
                  <dt>Destinations</dt>
                  <dd>{state.target_platforms.join(", ") || "Not selected"}</dd>
                </div>
                {project.data?.audience && (
                  <div>
                    <dt>Audience</dt>
                    <dd>{project.data.audience}</dd>
                  </div>
                )}
                {project.data?.tone && (
                  <div>
                    <dt>Tone</dt>
                    <dd>{project.data.tone}</dd>
                  </div>
                )}
              </dl>
              <p className="muted">
                Saved versions and originals stay intact as your workflow moves
                forward.
              </p>
            </aside>
          </div>
          <section className="operations-panel">
            <PanelHeading
              title="Background activity"
              description="Generation, analysis and rendering for this project."
              action={<span className="badge">{state.jobs.length} jobs</span>}
            />
            {state.jobs.length ? (
              state.jobs.map((j) => <Job key={j.id} id={j.id} />)
            ) : (
              <p className="muted">
                <Clock size={18} weight="light" /> No operations queued yet.
                Start with your script.
              </p>
            )}
          </section>
          {project.data && (
            <details className="studio-details">
              <summary>Edit project brief</summary>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const fields = new FormData(e.currentTarget);
                  action.run(() =>
                    patch(root, {
                      name: fields.get("name"),
                      brief: fields.get("brief"),
                      audience: fields.get("audience") || null,
                      tone: fields.get("tone") || null,
                    }),
                  );
                }}
              >
                <Field label="Project name">
                  <input
                    name="name"
                    defaultValue={project.data.name}
                    required
                  />
                </Field>
                <Field label="Brief">
                  <textarea
                    name="brief"
                    defaultValue={project.data.brief}
                    required
                  />
                </Field>
                <div className="columns">
                  <Field label="Audience">
                    <input
                      name="audience"
                      defaultValue={project.data.audience || ""}
                    />
                  </Field>
                  <Field label="Tone">
                    <input name="tone" defaultValue={project.data.tone || ""} />
                  </Field>
                </div>
                <button disabled={action.busy}>Save project details</button>
              </form>
            </details>
          )}
        </>
      )}
    </section>
  );
}
