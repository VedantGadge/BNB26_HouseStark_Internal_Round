"use client";
import { useState } from "react";
import { apiFetch, patch, post } from "@/lib/api";
import { Field, Media, Status, useAction, useApi } from "./common";
import { PageHeader } from "@/components/ui/studio-ui";
import { humanize, localDate } from "@/lib/creator.mjs";

function Publication({ record, root, revision, action }) {
  function fields(e) {
    e.preventDefault();
    return new FormData(e.currentTarget);
  }
  return (
    <article className="clip-row">
      <h2>
        {humanize(record.platform)}{" "}
        <span className="badge">{record.status}</span>
      </h2>
      {record.status === "published" ? (
        <p>
          Confirmed {new Date(record.published_at).toLocaleString()} ·{" "}
          <a href={record.external_url} target="_blank" rel="noreferrer">
            Published post
          </a>
        </p>
      ) : (
        <>
          <form
            onSubmit={(e) => {
              const f = fields(e);
              action.run(() =>
                patch(root + "/publications/" + record.id, {
                  expected_revision: revision,
                  planned_at: f.get("date")
                    ? new Date(f.get("date")).toISOString()
                    : null,
                  title: f.get("title"),
                  caption: f.get("caption"),
                }),
              );
            }}
          >
            <Field label="Planned date (your local timezone)">
              <input
                type="datetime-local"
                name="date"
                defaultValue={localDate(record.planned_at)}
              />
            </Field>
            {record.planned_at && (
              <p>
                Currently planned:{" "}
                {new Date(record.planned_at).toLocaleString()}
              </p>
            )}
            <Field label="Publication title">
              <input
                name="title"
                defaultValue={record.supporting_copy.title || ""}
                required
              />
            </Field>
            <Field label="Publication caption">
              <textarea
                name="caption"
                defaultValue={record.supporting_copy.caption || ""}
                required
              />
            </Field>
            <button disabled={action.busy}>Save plan & copy</button>
          </form>
          <form
            onSubmit={(e) => {
              const f = fields(e);
              action.run(() =>
                patch(root + "/publications/" + record.id, {
                  expected_revision: revision,
                  confirm_published: true,
                  external_url: f.get("url"),
                  published_at: new Date(f.get("actual")).toISOString(),
                }),
              );
            }}
          >
            <Field label="Actual publication date (your local timezone)">
              <input name="actual" type="datetime-local" required />
            </Field>
            <Field label="Published post URL">
              <input name="url" type="url" required />
            </Field>
            <button disabled={action.busy}>Confirm manual publication</button>
          </form>
        </>
      )}
    </article>
  );
}

export function Publish({ projectId }) {
  const root = `/projects/${projectId}`,
    workflow = useApi(root + "/workflow", true);
  const renders = useApi(root + "/exports", true),
    action = useAction();
  const [preview, setPreview] = useState(null);
  const state = workflow.data;
  return (
    <section className="workspace publish-workspace">
      <PageHeader
        title="Get your story ready."
        description="Review the final media, prepare each post and keep publication records connected."
        action={state && <span className="badge">{humanize(state.stage)}</span>}
      />
      <Status query={workflow} error={action.error} />
      <p>
        Download the approved exports, publish them on your chosen platform,
        then record the actual post.
      </p>
      {state && (
        <>
          <div className="notice">
            <p>{state.next_action}</p>
            {state.blocking_reasons.map((reason) => (
              <p key={reason}>{reason}</p>
            ))}
            {state.next_stage && (
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
          </div>
          <form
            className="package-form studio-panel"
            onSubmit={(e) => {
              e.preventDefault();
              const fields = new FormData(e.currentTarget);
              action.run(() =>
                patch(root + "/workflow", {
                  expected_revision: state.revision,
                  package: {
                    title: fields.get("title"),
                    caption: fields.get("caption"),
                    media_checked: fields.get("checked") === "on",
                    render_ids: fields.getAll("render"),
                  },
                }),
              );
            }}
          >
            <h2>Select completed exports</h2>
            {renders.data
              ?.filter((r) => r.processing_status === "completed" && r.platform)
              .map((r) => (
                <div key={r.id} className="row">
                  <label className="check">
                    <input
                      type="checkbox"
                      name="render"
                      value={r.id}
                      defaultChecked={state.package?.render_ids.includes(r.id)}
                    />
                    {r.platform} · {r.preset_name} · {r.supporting_copy.title}
                  </label>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setPreview(r.id)}
                  >
                    Play export
                  </button>
                </div>
              ))}
            <Field label="Package title">
              <input
                name="title"
                defaultValue={state.package?.title || state.name}
                required
                maxLength={160}
              />
            </Field>
            <Field label="Package caption">
              <textarea
                name="caption"
                defaultValue={state.package?.caption || state.brief}
                required
                maxLength={2000}
              />
            </Field>
            <label className="check">
              <input
                name="checked"
                type="checkbox"
                defaultChecked={state.package?.media_checked}
              />
              I played and checked the selected exports
            </label>
            <button disabled={action.busy || state.stage === "published"}>
              Save package for review
            </button>
          </form>
          {preview && <Media renderId={preview} />}
          {state.approved_package && (
            <button
              onClick={() =>
                action.run(async () => {
                  const body = await apiFetch(root + "/package");
                  const url = URL.createObjectURL(
                    new Blob([JSON.stringify(body, null, 2)], {
                      type: "application/json",
                    }),
                  );
                  const link = document.createElement("a");
                  link.href = url;
                  link.download = "creatorai-package.json";
                  link.click();
                  URL.revokeObjectURL(url);
                })
              }
            >
              Download package manifest & media links
            </button>
          )}
          <h2>Plan a platform</h2>
          <form
            className="publication-plan-form studio-panel"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              action.run(() =>
                post(root + "/publications", {
                  expected_revision: state.revision,
                  platform: f.get("platform"),
                  title: state.package?.title || state.name,
                  caption: state.package?.caption || state.brief,
                }),
              );
            }}
          >
            <Field label="Platform">
              <select name="platform">
                {(state.target_platforms.length
                  ? state.target_platforms
                  : ["instagram", "tiktok", "youtube", "linkedin"]
                ).map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </Field>
            <button disabled={action.busy}>Create publication plan</button>
          </form>
          {state.publications.map((record) => (
            <Publication
              key={record.id}
              record={record}
              root={root}
              revision={state.revision}
              action={action}
            />
          ))}
        </>
      )}
    </section>
  );
}
