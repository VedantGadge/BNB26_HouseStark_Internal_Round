"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { spokenScript } from "@/lib/creator.mjs";
import { useVersionedDraft } from "@/lib/use-versioned-draft";
import {
  Field,
  Job,
  Status,
  useAction,
  useApi,
} from "@/components/workflow/common";
import { Empty, Modal, PageHeader } from "@/components/ui/studio-ui";
import { CampaignBrief, StyleProfile, useScriptContext } from "./context";
import { Assistant } from "./assistant";
import { TrendPicker } from "./trends";

function RecordingRead({ text }) {
  const [size, setSize] = useState(28);
  return (
    <Modal
      title="Recording read"
      description="A distraction-free reading view. Scroll at your own pace; this does not record audio or video."
      className="recording"
      trigger={
        <button type="button" className="secondary">
          Recording read
        </button>
      }
    >
      <Field label="Reading text size">
        <input
          type="range"
          min="22"
          max="42"
          value={size}
          onChange={(event) => setSize(Number(event.target.value))}
        />
      </Field>
      <div className="recording-copy" style={{ fontSize: size }}>
        {text}
      </div>
    </Modal>
  );
}

export function ScriptWorkspace({ projectId }) {
  const root = `/projects/${projectId}/scripts`,
    versions = useApi(root + "/versions"),
    workflow = useApi(`/projects/${projectId}/workflow`, true);
  const { style, campaign } = useScriptContext(root);
  const action = useAction(),
    [job, setJob] = useState(null),
    [tab, setTab] = useState("Read"),
    [ack, setAck] = useState([]),
    [message, setMessage] = useState(""),
    [useStyle, setUseStyle] = useState(false),
    [trend, setTrend] = useState(null);
  const latest = versions.data?.[0],
    buffer = useVersionedDraft(
      latest,
      "content",
      `creatorai-draft:script:${projectId}`,
    ),
    draft = buffer.draft;
  const change = (key, value) => {
    buffer.setDraft((current) => ({ ...current, [key]: value }));
    setMessage("");
  };
  const activeJob =
    job ||
    workflow.data?.jobs.find((item) => item.type === "script_generation")?.id;
  const pending = workflow.data?.jobs.some(
    (item) =>
      item.type === "script_generation" &&
      ["queued", "running"].includes(item.status),
  );
  const spoken = spokenScript(draft);
  return (
    <section className="workspace script-workspace">
      <PageHeader
        title="Make it sound like you."
        description="A clear script, a stronger opening, your voice."
        action={
          latest && (
            <span className="badge">
              Version {latest.version} ·{" "}
              {buffer.dirty ? "Unsaved draft" : "Saved"}
            </span>
          )
        }
      />
      <Status query={versions} error={action.error} />
      <div className="two-pane">
        <div className="script-working-pane">
          <div className="tabs" aria-label="Script view">
            {["Read", "Edit", "Context"].map((value) => (
              <button
                type="button"
                key={value}
                aria-pressed={tab === value}
                onClick={() => setTab(value)}
              >
                {value}
              </button>
            ))}
          </div>
          {buffer.restored && (
            <p className="notice">
              Your unsaved script draft was restored from this browser session.
            </p>
          )}
          {buffer.stale && (
            <p className="notice">
              A newer saved version is available. Your draft has not been
              overwritten. Copy your changes before loading the latest version.
            </p>
          )}
          {message && (
            <p role="status" className="success">
              {message}
            </p>
          )}
          {draft && tab !== "Context" && (
            <>
              <div className="toolbar">
                <Field label="Version history">
                  <select
                    value={buffer.base?.id || ""}
                    onChange={(event) => {
                      const version = versions.data.find(
                        (v) => v.id === event.target.value,
                      );
                      buffer.setDraft(structuredClone(version.content));
                      setTab("Edit");
                      setMessage(
                        `Version ${version.version} loaded as a draft. Save to create a new version.`,
                      );
                    }}
                  >
                    {versions.data.map((version) => (
                      <option key={version.id} value={version.id}>
                        Version {version.version} · {version.origin}
                      </option>
                    ))}
                  </select>
                </Field>
                <span className="muted">
                  Editing from version {buffer.base?.version}
                </span>
              </div>
              {tab === "Read" ? (
                <>
                  <div className="read-toolbar">
                    <button
                      className="secondary"
                      onClick={() =>
                        action.run(async () => {
                          await navigator.clipboard.writeText(spoken);
                          setMessage("Spoken script copied.");
                        })
                      }
                    >
                      Copy spoken script
                    </button>
                    <RecordingRead text={spoken} />
                    <button
                      className="secondary"
                      onClick={() => setTab("Edit")}
                    >
                      Edit script
                    </button>
                  </div>
                  <div className="manuscript">{spoken}</div>
                  <details>
                    <summary>Supporting copy and production notes</summary>
                    <h3>{draft.title}</h3>
                    <p>{draft.description}</p>
                    <ul>
                      {draft.production_notes.map((note, index) => (
                        <li key={index}>{note}</li>
                      ))}
                    </ul>
                  </details>
                </>
              ) : (
                <form
                  className="script-edit"
                  onSubmit={(event) => {
                    event.preventDefault();
                    action.run(async () => {
                      const result = await post(root + "/versions", {
                        base_version: buffer.base.version,
                        content: draft,
                        acknowledged_warning_ids: ack,
                      });
                      buffer.reset(result);
                      setAck([]);
                      setMessage("New script version saved.");
                    });
                  }}
                >
                  <h2>Choose your opening</h2>
                  {draft.hooks.map((hook, index) => (
                    <div className="hook" key={hook.id}>
                      <label className="check">
                        <input
                          type="radio"
                          name="hook"
                          checked={draft.selected_hook_id === hook.id}
                          onChange={() => change("selected_hook_id", hook.id)}
                        />
                        Use hook {index + 1}
                      </label>
                      <Field label={`Hook ${index + 1}`}>
                        <textarea
                          value={hook.text}
                          required
                          maxLength={500}
                          onChange={(event) =>
                            change(
                              "hooks",
                              draft.hooks.map((item, i) =>
                                i === index
                                  ? { ...item, text: event.target.value }
                                  : item,
                              ),
                            )
                          }
                        />
                      </Field>
                    </div>
                  ))}
                  <h2>Your story</h2>
                  {draft.sections.map((section, index) => (
                    <Field key={section.id} label={section.heading}>
                      <textarea
                        value={section.text}
                        required
                        maxLength={3000}
                        onChange={(event) =>
                          change(
                            "sections",
                            draft.sections.map((item, i) =>
                              i === index
                                ? { ...item, text: event.target.value }
                                : item,
                            ),
                          )
                        }
                      />
                    </Field>
                  ))}
                  {[
                    ["call_to_action", "Call to action", 500],
                    ["title", "Supporting title", 160],
                    ["description", "Supporting description", 2000],
                  ].map(([key, label, max]) => (
                    <Field key={key} label={label}>
                      <textarea
                        value={draft[key]}
                        required
                        maxLength={max}
                        onChange={(event) => change(key, event.target.value)}
                      />
                    </Field>
                  ))}
                  {buffer.base.requirement_checks.map((check) => (
                    <p
                      key={check.requirement_id}
                      className={
                        check.status === "satisfied" ? "muted" : "error"
                      }
                    >
                      {check.status}: {check.message || check.requirement_id}
                    </p>
                  ))}
                  {buffer.base.warning_ids.map((id) => (
                    <label key={id} className="check">
                      <input
                        type="checkbox"
                        checked={ack.includes(id)}
                        onChange={(event) =>
                          setAck(
                            event.target.checked
                              ? [...ack, id]
                              : ack.filter((v) => v !== id),
                          )
                        }
                      />
                      I reviewed warning: {id}
                    </label>
                  ))}
                  <button
                    disabled={
                      action.busy ||
                      buffer.stale ||
                      buffer.base.warning_ids.some((id) => !ack.includes(id))
                    }
                  >
                    Save script version
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => {
                      buffer.reset();
                      setAck([]);
                      setMessage("Latest saved script loaded.");
                    }}
                  >
                    Load latest / revert draft
                  </button>
                </form>
              )}
              {buffer.stale && (
                <button
                  className="secondary"
                  onClick={() =>
                    action.run(async () => {
                      await navigator.clipboard.writeText(
                        JSON.stringify(draft, null, 2),
                      );
                      setMessage(
                        "Your draft was copied before loading the latest version.",
                      );
                    })
                  }
                >
                  Copy entire draft before refreshing
                </button>
              )}
            </>
          )}
          {!draft && tab !== "Context" && !versions.isPending && (
            <Empty title="The first line is yours">
              Generate a script from your project brief, then choose a hook and
              make it your own.
            </Empty>
          )}
          {tab === "Context" && (
            <>
              <CampaignBrief root={root} query={campaign} />
              <StyleProfile query={style} />
            </>
          )}
        </div>
        <aside className="inspector">
          <h2>Generate a new script</h2>
          <p className="muted">
            Use the saved project brief and context. Each result becomes a new
            version.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const f = new FormData(event.currentTarget);
              action.run(async () => {
                const queued = await post(
                  root + "/generate",
                  {
                    target_duration_seconds: Number(f.get("duration")),
                    language: f.get("language"),
                    use_style_profile: useStyle && Boolean(style.data),
                    ...(trend ? { trend } : {}),
                    ...(useStyle && style.data
                      ? {
                          style_profile_revision: style.data.revision,
                          optional_signature_line_ids: f.getAll("signature"),
                        }
                      : {}),
                    ...(campaign.data
                      ? { campaign_brief_revision: campaign.data.revision }
                      : {}),
                  },
                  true,
                );
                setJob(queued.id);
                setMessage(
                  "Generation queued. Your current draft is preserved.",
                );
              });
            }}
          >
            <Field label="Target duration (seconds)">
              <input
                name="duration"
                type="number"
                min="15"
                max="300"
                defaultValue="60"
                required
              />
            </Field>
            <Field label="Language">
              <select name="language">
                {["english", "hindi", "hinglish"].map((language) => (
                  <option key={language}>{language}</option>
                ))}
              </select>
            </Field>
            <p className="muted">
              Mode: {campaign.data?.content_mode || "personal"}
              {campaign.data
                ? ` · context revision ${campaign.data.revision}`
                : ""}
            </p>
            <button
              type="button"
              className="secondary"
              onClick={() => setTab("Context")}
            >
              Manage context
            </button>
            <label className="check">
              <input
                type="checkbox"
                checked={useStyle && Boolean(style.data)}
                disabled={!style.data}
                onChange={(event) => setUseStyle(event.target.checked)}
              />
              Use saved creator style
              {style.data ? ` · revision ${style.data.revision}` : ""}
            </label>
            {useStyle &&
              style.data?.profile.signature_lines
                .filter((line) => line.inclusion_policy === "on_request")
                .map((line) => (
                  <label className="check" key={line.id}>
                    <input type="checkbox" name="signature" value={line.id} />
                    {line.text}
                  </label>
                ))}
            <TrendPicker root={root} selected={trend} onSelect={setTrend} />
            <button
              disabled={
                action.busy || pending || style.isPending || campaign.isPending
              }
            >
              Generate hooks and script
            </button>
          </form>
          <Job id={activeJob} onDone={() => versions.refetch()} />
          {latest?.input_snapshot.selected_trend && (
            <details>
              <summary>Trend context for version {latest.version}</summary>
              <p>{latest.input_snapshot.selected_trend.topic.title}</p>
              <p className="muted">
                Google Trends ·{" "}
                {latest.input_snapshot.selected_trend.topic.country}
                {" · "}fetched{" "}
                {new Date(
                  latest.input_snapshot.selected_trend.fetched_at,
                ).toLocaleString()}
              </p>
              <a
                href={latest.input_snapshot.selected_trend.topic.source_url}
                target="_blank"
                rel="noreferrer"
              >
                View source
              </a>
            </details>
          )}
        </aside>
      </div>
      {latest && (
        <Assistant
          root={root}
          latest={latest}
          dirty={buffer.dirty}
          onApplied={(version) => {
            buffer.reset(version);
            setMessage("Reviewed proposal saved as a new script version.");
          }}
        />
      )}
    </section>
  );
}
