"use client";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, post } from "@/lib/api";
import { presets, remapTrim } from "@/lib/creator.mjs";
import { useVersionedDraft } from "@/lib/use-versioned-draft";
import { Empty, PageHeader } from "@/components/ui/studio-ui";
import { Field, Job, Media, Status, useAction, useApi } from "./common";

const RecipePlayer = dynamic(
  () => import("@/components/remotion/recipe-player"),
  {
    ssr: false,
    loading: () => <p role="status">Loading live layout preview…</p>,
  },
);
export { remapTrim } from "@/lib/creator.mjs";

export function Editor({ projectId, clipId }) {
  const clip = useApi(`/clips/${clipId}`),
    assets = useApi(`/projects/${projectId}/assets`),
    workflow = useApi(`/projects/${projectId}/workflow`, true),
    renders = useApi(`/projects/${projectId}/exports`, true),
    action = useAction();
  const [job, setJob] = useState(null),
    [preview, setPreview] = useState(null),
    [tab, setTab] = useState("Edit"),
    [preset, setPreset] = useState("instagram_reel"),
    [safe, setSafe] = useState(false),
    [message, setMessage] = useState("");
  const latest = clip.data?.versions[0],
    buffer = useVersionedDraft(
      latest,
      "recipe",
      `creatorai-draft:edit:${clipId}`,
    ),
    recipe = buffer.draft;
  const candidate = clip.data?.candidate,
    source = assets.data?.find((asset) => asset.id === candidate?.asset_id);
  const deliveryPath = candidate
    ? `/assets/${candidate.asset_id}/delivery`
    : null;
  const delivery = useQuery({
    queryKey: [deliveryPath],
    queryFn: () => apiFetch(deliveryPath),
    enabled: Boolean(deliveryPath),
    refetchInterval: 240000,
  });
  const change = (key, value) => {
    buffer.setDraft((r) => ({ ...r, [key]: value }));
    setMessage("");
  };
  const reviewJob = workflow.data?.jobs.find(
    (j) => j.type === "clip_generation" && j.status === "waiting_review",
  );
  const selectedPreset = presets.find((p) => p.id === preset);
  const completed =
    renders.data?.filter(
      (render) =>
        render.edit_version_id === latest?.id &&
        render.processing_status === "completed",
    ) || [];
  const valid =
    recipe &&
    recipe.source_end_ms - recipe.source_start_ms >= 2000 &&
    recipe.source_end_ms - recipe.source_start_ms <= 60000 &&
    recipe.source_start_ms >= 0 &&
    (!source?.duration_ms || recipe.source_end_ms <= source.duration_ms);
  return (
    <section className="workspace editor-workspace">
      <Link className="text-link" href={`/projects/${projectId}/clips`}>
        Back to clips
      </Link>
      <PageHeader
        title="Shape the moment."
        description={
          candidate?.hook || "A precise edit. A story that stays yours."
        }
        action={
          latest && (
            <span className="badge">
              Version {latest.revision} · {buffer.dirty ? "Unsaved" : "Saved"}
            </span>
          )
        }
      />
      <Status query={clip} error={action.error} />
      {!latest && candidate && (
        <Empty
          title="Start with an assisted edit"
          action={
            <button
              disabled={action.busy}
              onClick={() =>
                action.run(() =>
                  post(`/clip-candidates/${clipId}/edit-versions`, {}),
                )
              }
            >
              Create assisted edit recipe
            </button>
          }
        >
          The original source stays intact. Your trim, captions and framing will
          be saved as a versioned recipe.
        </Empty>
      )}
      {recipe && (
        <>
          <div className="two-pane wide">
            <div>
              <div className="editing-preview">
                <Status query={delivery} />
                {delivery.data && valid && (
                  <RecipePlayer
                    src={delivery.data.url}
                    recipe={recipe}
                    showSafeZones={safe}
                  />
                )}
                <p className="muted">
                  Live layout preview. Verified FFmpeg exports provide final
                  fonts, timing and normalized audio.
                </p>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={safe}
                    onChange={(event) => setSafe(event.target.checked)}
                  />
                  Show output safe zones
                </label>
                <button
                  className="secondary"
                  onClick={() => delivery.refetch()}
                >
                  Refresh source link
                </button>
              </div>
              {source?.duration_ms && (
                <div
                  className="timeline-range"
                  role="img"
                  aria-label={`Selected source range ${recipe.source_start_ms / 1000} to ${recipe.source_end_ms / 1000} seconds`}
                >
                  <span
                    style={{
                      left: `${(recipe.source_start_ms / source.duration_ms) * 100}%`,
                      width: `${((recipe.source_end_ms - recipe.source_start_ms) / source.duration_ms) * 100}%`,
                    }}
                  />
                </div>
              )}
              {buffer.stale && (
                <p className="notice">
                  A newer saved edit exists. Your draft is preserved. Load the
                  latest version before saving; copy your changes first if
                  needed.
                </p>
              )}
              {buffer.stale && (
                <button
                  className="secondary"
                  onClick={() =>
                    action.run(async () => {
                      await navigator.clipboard.writeText(
                        JSON.stringify(recipe, null, 2),
                      );
                      setMessage("Entire edit draft copied.");
                    })
                  }
                >
                  Copy edit draft before refreshing
                </button>
              )}
              {buffer.restored && (
                <p className="notice">Your unsaved edit draft was restored.</p>
              )}
              {message && (
                <p role="status" className="success">
                  {message}
                </p>
              )}
              <details>
                <summary>Original source playback</summary>
                {candidate && (
                  <Media
                    assetId={candidate.asset_id}
                    seek={recipe.source_start_ms / 1000}
                  />
                )}
              </details>
            </div>
            <aside className="inspector">
              <div className="tabs" aria-label="Editor controls">
                {["Edit", "Export"].map((value) => (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={tab === value}
                    onClick={() => setTab(value)}
                  >
                    {value}
                  </button>
                ))}
              </div>
              {tab === "Edit" ? (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    action.run(async () => {
                      const saved = await post(
                        `/clip-candidates/${clipId}/edit-versions`,
                        { base_version_id: buffer.base.id, recipe },
                      );
                      buffer.reset(saved);
                      setMessage("New edit version saved.");
                    });
                  }}
                >
                  <h2>Edit recipe</h2>
                  <Field label="Load earlier recipe">
                    <select
                      value={buffer.base?.id || ""}
                      onChange={(event) => {
                        const version = clip.data.versions.find(
                          (v) => v.id === event.target.value,
                        );
                        buffer.setDraft(structuredClone(version.recipe));
                        setMessage(
                          `Version ${version.revision} loaded as a draft. Save to create a new version.`,
                        );
                      }}
                    >
                      {clip.data.versions.map((version) => (
                        <option key={version.id} value={version.id}>
                          Version {version.revision}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <h3>Source range</h3>
                  <div className="columns">
                    <Field label="Source start (seconds)">
                      <input
                        type="number"
                        min="0"
                        max={(source?.duration_ms || 3600000) / 1000}
                        step="0.1"
                        value={recipe.source_start_ms / 1000}
                        onChange={(event) =>
                          buffer.setDraft((r) =>
                            remapTrim(
                              r,
                              Math.round(Number(event.target.value) * 1000),
                              r.source_end_ms,
                            ),
                          )
                        }
                      />
                    </Field>
                    <Field label="Source end (seconds)">
                      <input
                        type="number"
                        min="2"
                        max={(source?.duration_ms || 3600000) / 1000}
                        step="0.1"
                        value={recipe.source_end_ms / 1000}
                        onChange={(event) =>
                          buffer.setDraft((r) =>
                            remapTrim(
                              r,
                              r.source_start_ms,
                              Math.round(Number(event.target.value) * 1000),
                            ),
                          )
                        }
                      />
                    </Field>
                  </div>
                  {!valid && (
                    <p className="error" role="alert">
                      Choose a 2 to 60 second range within the source video.
                    </p>
                  )}
                  <h3>Frame</h3>
                  <Field label="Edit canvas">
                    <select
                      value={`${recipe.output.width}:${recipe.output.height}`}
                      onChange={(event) => {
                        const [width, height] = event.target.value
                          .split(":")
                          .map(Number);
                        change("output", {
                          ...recipe.output,
                          width,
                          height,
                          safe_top_px: 80,
                          safe_bottom_px: height > width ? 150 : 100,
                        });
                      }}
                    >
                      <option value="1080:1920">Portrait · 9:16</option>
                      <option value="1080:1080">Square · 1:1</option>
                      <option value="1920:1080">Landscape · 16:9</option>
                    </select>
                  </Field>
                  <Field label="Fit">
                    <select
                      value={recipe.output.fit}
                      onChange={(event) =>
                        change("output", {
                          ...recipe.output,
                          fit: event.target.value,
                        })
                      }
                    >
                      <option value="crop">Crop to fill</option>
                      <option value="pad">Pad to fit</option>
                    </select>
                  </Field>
                  {[
                    ["center_x", "Crop horizontal position"],
                    ["center_y", "Crop vertical position"],
                  ].map(([key, label]) => (
                    <Field key={key} label={label}>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={recipe.crop[key]}
                        onChange={(event) =>
                          change("crop", {
                            ...recipe.crop,
                            [key]: Number(event.target.value),
                          })
                        }
                      />
                    </Field>
                  ))}
                  <h3>Captions</h3>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={recipe.captions_enabled}
                      onChange={(event) =>
                        change("captions_enabled", event.target.checked)
                      }
                    />
                    Captions enabled
                  </label>
                  <Field label="Caption style">
                    <select
                      value={recipe.caption_style}
                      onChange={(event) =>
                        change("caption_style", event.target.value)
                      }
                    >
                      {[
                        ["clean", "Clean"],
                        ["bold", "Bold"],
                        ["bold_highlight", "Bold highlight"],
                      ].map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </Field>
                  {recipe.captions.map((caption, index) => (
                    <div key={index}>
                      <Field label={`Caption ${index + 1}`}>
                        <textarea
                          value={caption.text}
                          maxLength={240}
                          required
                          onChange={(event) =>
                            change(
                              "captions",
                              recipe.captions.map((item, i) =>
                                i === index
                                  ? { ...item, text: event.target.value }
                                  : item,
                              ),
                            )
                          }
                        />
                      </Field>
                      <div className="columns">
                        {[
                          ["start_ms", "Caption start"],
                          ["end_ms", "Caption end"],
                        ].map(([key, label]) => (
                          <Field
                            key={key}
                            label={`${label} ${index + 1} (seconds)`}
                          >
                            <input
                              type="number"
                              min="0"
                              max={
                                (recipe.source_end_ms -
                                  recipe.source_start_ms) /
                                1000
                              }
                              step="0.1"
                              value={caption[key] / 1000}
                              onChange={(event) =>
                                change(
                                  "captions",
                                  recipe.captions.map((item, i) =>
                                    i === index
                                      ? {
                                          ...item,
                                          [key]: Math.round(
                                            Number(event.target.value) * 1000,
                                          ),
                                        }
                                      : item,
                                  ),
                                )
                              }
                            />
                          </Field>
                        ))}
                      </div>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() =>
                          change(
                            "captions",
                            recipe.captions.filter((_, i) => i !== index),
                          )
                        }
                      >
                        Remove caption {index + 1}
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    className="secondary"
                    disabled={recipe.captions.length >= 20 || !valid}
                    onClick={() =>
                      change("captions", [
                        ...recipe.captions,
                        {
                          start_ms: 0,
                          end_ms: Math.min(
                            3000,
                            recipe.source_end_ms - recipe.source_start_ms,
                          ),
                          text: "New caption",
                        },
                      ])
                    }
                  >
                    Add caption
                  </button>
                  <h3>Opening title</h3>
                  {recipe.title ? (
                    <>
                      <Field label="Opening title">
                        <input
                          value={recipe.title.text}
                          required
                          maxLength={140}
                          onChange={(event) =>
                            change("title", {
                              ...recipe.title,
                              text: event.target.value,
                            })
                          }
                        />
                      </Field>
                      <Field label="Title position">
                        <select
                          value={recipe.title.position}
                          onChange={(event) =>
                            change("title", {
                              ...recipe.title,
                              position: event.target.value,
                            })
                          }
                        >
                          <option value="top">Top safe zone</option>
                          <option value="bottom">Bottom safe zone</option>
                        </select>
                      </Field>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => change("title", null)}
                      >
                        Remove title
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="secondary"
                      onClick={() =>
                        change("title", {
                          text: candidate.hook.slice(0, 140),
                          start_ms: 0,
                          end_ms: Math.min(
                            3000,
                            recipe.source_end_ms - recipe.source_start_ms,
                          ),
                          position: "top",
                        })
                      }
                    >
                      Add opening title
                    </button>
                  )}
                  <details>
                    <summary>Emphasis zoom and audio</summary>
                    {recipe.emphasis_zooms.map((zoom, index) => (
                      <div key={index}>
                        <div className="columns">
                          {[
                            ["start_ms", "Zoom start"],
                            ["end_ms", "Zoom end"],
                          ].map(([key, label]) => (
                            <Field
                              key={key}
                              label={`${label} ${index + 1} (seconds)`}
                            >
                              <input
                                type="number"
                                min="0"
                                max={
                                  (recipe.source_end_ms -
                                    recipe.source_start_ms) /
                                  1000
                                }
                                step="0.1"
                                value={zoom[key] / 1000}
                                onChange={(event) =>
                                  change(
                                    "emphasis_zooms",
                                    recipe.emphasis_zooms.map((item, i) =>
                                      i === index
                                        ? {
                                            ...item,
                                            [key]: Math.round(
                                              Number(event.target.value) * 1000,
                                            ),
                                          }
                                        : item,
                                    ),
                                  )
                                }
                              />
                            </Field>
                          ))}
                        </div>
                        <Field label={`Zoom scale ${index + 1}`}>
                          <input
                            type="range"
                            min="1.02"
                            max="1.2"
                            step="0.01"
                            value={zoom.scale}
                            onChange={(event) =>
                              change(
                                "emphasis_zooms",
                                recipe.emphasis_zooms.map((item, i) =>
                                  i === index
                                    ? {
                                        ...item,
                                        scale: Number(event.target.value),
                                      }
                                    : item,
                                ),
                              )
                            }
                          />
                        </Field>
                        <button
                          type="button"
                          className="secondary"
                          onClick={() =>
                            change(
                              "emphasis_zooms",
                              recipe.emphasis_zooms.filter(
                                (_, i) => i !== index,
                              ),
                            )
                          }
                        >
                          Remove zoom {index + 1}
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      className="secondary"
                      disabled={recipe.emphasis_zooms.length >= 2 || !valid}
                      onClick={() =>
                        change("emphasis_zooms", [
                          ...recipe.emphasis_zooms,
                          {
                            start_ms: 0,
                            end_ms: Math.min(
                              3000,
                              recipe.source_end_ms - recipe.source_start_ms,
                            ),
                            scale: 1.08,
                          },
                        ])
                      }
                    >
                      Add emphasis zoom
                    </button>
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={recipe.audio.normalize}
                        onChange={(event) =>
                          change("audio", {
                            ...recipe.audio,
                            normalize: event.target.checked,
                          })
                        }
                      />
                      Normalize exported audio
                    </label>
                    {[
                      ["fade_in_ms", "Audio fade in"],
                      ["fade_out_ms", "Audio fade out"],
                    ].map(([key, label]) => (
                      <Field key={key} label={`${label} (milliseconds)`}>
                        <input
                          type="number"
                          min="0"
                          max="1000"
                          value={recipe.audio[key]}
                          onChange={(event) =>
                            change("audio", {
                              ...recipe.audio,
                              [key]: Number(event.target.value),
                            })
                          }
                        />
                      </Field>
                    ))}
                  </details>
                  <button disabled={action.busy || !valid || buffer.stale}>
                    Save edit version
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => {
                      buffer.reset();
                      setMessage("Latest saved edit loaded.");
                    }}
                  >
                    Revert unsaved changes
                  </button>
                </form>
              ) : (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    const f = new FormData(event.currentTarget);
                    action.run(async () => {
                      const queued = await post(
                        `/clips/${clipId}/exports`,
                        {
                          edit_version_id: latest.id,
                          preset,
                          platform: selectedPreset.platform,
                          fit: f.get("fit"),
                          title: f.get("title"),
                          caption: f.get("caption"),
                          hashtags: String(f.get("hashtags") || "")
                            .split(/\s+/)
                            .filter(Boolean),
                        },
                        true,
                      );
                      setJob(queued.id);
                    });
                  }}
                >
                  <h3>Export saved version {latest.revision}</h3>
                  {buffer.dirty && (
                    <p className="notice">
                      Unsaved changes are not exported. Save your edit first, or
                      export the last saved version.
                    </p>
                  )}
                  <Field label="Platform preset">
                    <select
                      value={preset}
                      onChange={(event) => setPreset(event.target.value)}
                    >
                      {presets.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} · {p.width}×{p.height}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <p className="muted">
                    {selectedPreset.platform} · safe top{" "}
                    {selectedPreset.safeTop}px · bottom{" "}
                    {selectedPreset.safeBottom}px
                  </p>
                  <Field label="Framing">
                    <select name="fit">
                      <option value="crop">Crop to fill</option>
                      <option value="pad">Pad to fit</option>
                    </select>
                  </Field>
                  <Field label="Platform title">
                    <input
                      name="title"
                      required
                      maxLength={160}
                      defaultValue={candidate.hook.slice(0, 160)}
                    />
                  </Field>
                  <Field label="Platform caption">
                    <textarea
                      name="caption"
                      required
                      maxLength={2000}
                      defaultValue={candidate.transcript_text || candidate.hook}
                    />
                  </Field>
                  <Field label="Hashtags (space separated)">
                    <input name="hashtags" />
                  </Field>
                  <button disabled={action.busy}>Queue export</button>
                  <p className="muted">
                    Each export has independent copy and a verified physical
                    MP4.
                  </p>
                </form>
              )}
            </aside>
          </div>
          {reviewJob && (
            <button
              disabled={action.busy || buffer.dirty}
              onClick={() =>
                action.run(() =>
                  post(`/jobs/${reviewJob.id}/review`, {
                    edit_version_id: latest.id,
                  }),
                )
              }
            >
              Complete review with saved edit
            </button>
          )}
          <Job
            id={job}
            onDone={(result) => setPreview(result.result.export_id)}
          />
          <h2>Verified exports</h2>
          <div className="export-list">
            {completed.map((render) => (
              <button
                className="secondary"
                key={render.id}
                onClick={() => setPreview(render.id)}
              >
                {render.preset_name} · {render.width}×{render.height}
              </button>
            ))}
          </div>
          {completed.length === 0 && (
            <p className="muted">
              Queue an export to check the authoritative result, then prepare
              your package.
            </p>
          )}
        </>
      )}
      {preview && <Media renderId={preview} />}
      <Link className="text-link" href={`/projects/${projectId}/publish`}>
        Prepare publication package
      </Link>
    </section>
  );
}
