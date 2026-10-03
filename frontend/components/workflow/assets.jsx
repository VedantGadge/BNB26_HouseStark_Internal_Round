"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { uploadFile } from "@/lib/upload";
import { Field, Job, Media, Status, time, useAction, useApi } from "./common";

function Evidence({ asset }) {
  const analysis = useApi(`/assets/${asset.id}/analysis`, asset.processing_status !== "ready");
  const alignment = useApi(`/assets/${asset.id}/script-alignments`);
  const [seek, setSeek] = useState(0);
  return <div><Media assetId={asset.id} kind={asset.kind} seek={seek} /><Status query={analysis} />
    <h3>Transcript</h3>{analysis.data?.transcript_segments.map((s) => <button className="evidence" key={s.id} onClick={() => setSeek(s.source_start_ms / 1000)}>{time(s.source_start_ms)} · {s.text}</button>)}
    <h3>Visual evidence</h3>{analysis.data?.visual_observations.map((v) => <button className="evidence" key={v.id} onClick={() => setSeek(v.source_start_ms / 1000)}>{time(v.source_start_ms)} · {v.description}</button>)}
    <h3>Script matches</h3>{alignment.data?.length ? alignment.data.map((a) => <div key={a.id}>
      <button className="evidence" disabled={a.match_status === "unmatched"} onClick={() => setSeek(a.source_start_ms / 1000)}>{a.match_status} · {a.script_beat} · {Math.round(a.confidence * 100)}% match confidence</button>
      <p>{a.evidence_text}</p>{a.visual_evidence.map((v) => <p key={v.id}>Visual: {v.description}</p>)}
    </div>) : <p>Generate clips to align the saved script with source evidence.</p>}
  </div>;
}

export function Assets({ projectId }) {
  const assets = useApi(`/projects/${projectId}/assets`, true);
  const workflow = useApi(`/projects/${projectId}/workflow`, true);
  const action = useAction();
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [progress, setProgress] = useState(null);
  const selectedAsset = assets.data?.find((a) => a.id === selected);
  return <section className="workspace"><h1>Assets & source evidence</h1><Status query={assets} error={action.error} />
    <form onSubmit={(e) => { e.preventDefault(); const fields = new FormData(e.currentTarget);
      action.run(async () => {
        const file = fields.get("file"); const kind = file.type.split("/")[0];
        if (!["video", "image", "audio"].includes(kind)) throw new Error("Choose a video, image, or audio file.");
        if (file.size > 100000000) throw new Error("Files must be smaller than 100 MB.");
        setProgress(0);
        try {
          const upload = await post(`/projects/${projectId}/assets/upload-session`, { filename: file.name,
            byte_size: file.size, content_type: file.type, kind, tags: String(fields.get("tags") || "").split(",").map((s) => s.trim()).filter(Boolean) });
          const result = await uploadFile(upload, file, setProgress);
          await post(`/assets/${upload.asset_id}/complete`, { provider_asset_id: result.asset_id, provider_version: String(result.version) });
          setSelected(upload.asset_id);
        } finally { setProgress(null); }
      });
    }}>
      <Field label="Video, image, or audio · up to 100 MB"><input name="file" type="file" accept="video/*,image/*,audio/*" required /></Field>
      <Field label="Tags (comma separated)"><input name="tags" /></Field><button disabled={action.busy}>Upload asset</button>
      {progress !== null && <progress max="100" value={progress} aria-label="Upload progress" />}
    </form>
    <div className="columns"><Field label="Media type"><select value={filter} onChange={(e) => setFilter(e.target.value)}>{["all", "video", "image", "audio"].map((v) => <option key={v}>{v}</option>)}</select></Field>
      <Field label="Search tags"><input value={search} onChange={(e) => setSearch(e.target.value)} /></Field></div>
    <div className="rows">{assets.data?.filter((a) => (filter === "all" || a.kind === filter) && a.tags.join(" ").toLowerCase().includes(search.toLowerCase())).map((a) => <button className="row secondary" key={a.id} onClick={() => setSelected(a.id)}><strong>{a.kind} · {a.tags.join(", ") || a.id.slice(0, 8)}</strong><span>{a.processing_status} {a.duration_ms ? time(a.duration_ms) : ""}</span>{a.processing_error && <span className="error">{a.processing_error}</span>}</button>)}</div>
    {assets.data?.length === 0 && <p>Upload footage to begin the media workflow.</p>}
    {workflow.data?.jobs.filter((j) => j.type === "asset_ingestion").map((j) => <Job key={j.id} id={j.id} />)}
    {selectedAsset && <Evidence key={selectedAsset.id} asset={selectedAsset} />}
  </section>;
}
