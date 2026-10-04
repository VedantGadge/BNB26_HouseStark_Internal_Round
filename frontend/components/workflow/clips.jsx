"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { post } from "@/lib/api";
import { Field, Job, Media, Status, time, useAction, useApi } from "./common";
import { Empty, PageHeader, PanelHeading } from "@/components/ui/studio-ui";

export function Clips({ projectId }) {
  const assets = useApi(`/projects/${projectId}/assets`);
  const clips = useApi(`/projects/${projectId}/clips`, true);
  const exports = useApi(`/projects/${projectId}/exports`, true);
  const workflow = useApi(`/projects/${projectId}/workflow`, true);
  const action = useAction();
  const [job, setJob] = useState(null);
  const [preview, setPreview] = useState(null);
  const router = useRouter();
  const ready =
    assets.data?.filter(
      (a) => a.kind === "video" && a.processing_status === "ready",
    ) || [];
  return (
    <section className="workspace clips-workspace">
      <PageHeader
        title="Find the moments worth keeping."
        description="Suggestions grounded in your footage. Your judgment makes the final cut."
      />
      <Status query={clips} error={action.error} />
      <div className="clip-builder">
        <PanelHeading
          title="From source to short"
          description="Let the saved script guide your selection, or choose your own range."
        />
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const assetId = new FormData(e.currentTarget).get("asset");
            action.run(async () => {
              const queued = await post(
                `/projects/${projectId}/clips/generate`,
                { asset_id: assetId, max_candidates: 3 },
                true,
              );
              setJob(queued.id);
            });
          }}
        >
          <Field label="Analyzed source video">
            <select name="asset" required>
              <option value="">Choose source</option>
              {assets.data
                ?.filter(
                  (a) => a.kind === "video" && a.processing_status === "ready",
                )
                .map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.tags.join(", ") || a.id.slice(0, 8)} ·{" "}
                    {time(a.duration_ms)}
                  </option>
                ))}
            </select>
          </Field>
          <button disabled={action.busy || !ready.length}>
            Find up to three clips
          </button>
        </form>
        <details>
          <summary>Choose a source range yourself</summary>
          <p className="muted">
            Use an analyzed video and select a range lasting 2 to 60 seconds.
            Manual selection does not claim an AI match.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const f = new FormData(event.currentTarget);
              action.run(async () => {
                const candidate = await post(
                  `/projects/${projectId}/clips/manual`,
                  {
                    asset_id: f.get("asset"),
                    source_start_ms: Math.round(Number(f.get("start")) * 1000),
                    source_end_ms: Math.round(Number(f.get("end")) * 1000),
                    title: f.get("title"),
                  },
                );
                router.push(`/projects/${projectId}/clips/${candidate.id}`);
              });
            }}
          >
            <Field label="Manual source video">
              <select name="asset" required>
                <option value="">Choose source</option>
                {ready.map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.tags.join(", ") || asset.id.slice(0, 8)} ·{" "}
                    {time(asset.duration_ms)}
                  </option>
                ))}
              </select>
            </Field>
            <div className="columns">
              <Field label="Manual start (seconds)">
                <input name="start" type="number" min="0" step="0.1" required />
              </Field>
              <Field label="Manual end (seconds)">
                <input name="end" type="number" min="2" step="0.1" required />
              </Field>
            </div>
            <Field label="Clip title">
              <input name="title" required maxLength={160} />
            </Field>
            <button disabled={action.busy || !ready.length}>
              Create manual clip
            </button>
          </form>
        </details>
      </div>
      <Job id={job} />
      {workflow.data?.jobs
        .filter((j) => j.type === "clip_generation" && j.id !== job)
        .slice(0, 3)
        .map((j) => (
          <Job key={j.id} id={j.id} />
        ))}
      <div className="rows clip-grid">
        {clips.data?.map((clip) => (
          <article key={clip.id} className="clip-row">
            <h2>{clip.hook}</h2>
            <p>
              {time(clip.source_start_ms)} to {time(clip.source_end_ms)} ·{" "}
              {clip.reasons.includes("creator-selected-source-range")
                ? "Creator-selected range"
                : `${Math.round(clip.score * 100)}% match confidence`}
            </p>
            {clip.is_stale && (
              <p className="notice">
                Based on an earlier script version. This edit is preserved.{" "}
                <Link
                  className="text-link"
                  href={`/projects/${projectId}/script`}
                >
                  Review current script
                </Link>
              </p>
            )}
            <p className="muted">
              Source script version:{" "}
              {clip.script_version_id?.slice(0, 8) || "manual alignment"}
            </p>
            <p>{clip.transcript_text}</p>
            <p className="muted">
              Evidence: {clip.reasons.join(", ")}. Ranking is a review
              heuristic.
            </p>
            <Link
              className="button"
              href={`/projects/${projectId}/clips/${clip.id}`}
            >
              Edit this clip
            </Link>
          </article>
        ))}
      </div>
      {clips.data?.length === 0 && (
        <Empty title="Your source comes first">
          Analyze a video and save a script, or choose a source range manually.
          Grounded proposals appear here as the worker finishes.
        </Empty>
      )}
      <div className="export-shelf">
        <h2>Rendered previews & exports</h2>
        {exports.data
          ?.filter((r) => r.processing_status === "completed")
          .map((r) => (
            <button
              key={r.id}
              className="secondary"
              onClick={() => setPreview(r.id)}
            >
              {r.preset_name} · {r.supporting_copy.title || "Draft preview"}
            </button>
          ))}
        {preview && <Media renderId={preview} />}
        {!exports.isPending &&
          !exports.data?.some((r) => r.processing_status === "completed") && (
            <p className="muted">
              Saved renders will appear here after an export completes.
            </p>
          )}
      </div>
    </section>
  );
}
