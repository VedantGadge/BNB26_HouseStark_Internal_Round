"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, post } from "@/lib/api";

export function useApi(path, poll = false) {
  return useQuery({ queryKey: [path], queryFn: () => apiFetch(path),
    enabled: Boolean(path), refetchInterval: poll ? 3000 : false });
}

export function useAction() {
  const cache = useQueryClient();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function run(action) {
    setError(""); setBusy(true);
    try {
      const result = await action();
      await cache.invalidateQueries();
      return result;
    } catch (failure) { setError(failure.message); return null; }
    finally { setBusy(false); }
  }
  return { error, busy, run };
}

export function Status({ query, error }) {
  return <>{query?.isPending && <p role="status">Loading…</p>}
    {(error || query?.error?.message) && <p role="alert" className="error">{error || query.error.message}</p>}</>;
}

export function Field({ label, children }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}

export function Job({ id, onDone }) {
  const query = useApi(id ? `/jobs/${id}` : null, true);
  const action = useAction();
  const notified = useRef(null);
  useEffect(() => {
    if (query.data?.status === "completed" && notified.current !== id) {
      notified.current = id; onDone?.(query.data);
    }
  }, [query.data, id, onDone]);
  if (!id) return null;
  return <div className="job" aria-live="polite"><Status query={query} error={action.error} />
    {query.data && <><p>{query.data.status} · {query.data.stage.replaceAll("_", " ")}</p>
      {query.data.error && <p className="error">{query.data.error}</p>}
      {query.data.status === "waiting_review" && <p>Drafts are ready. Open a clip, save your changes, then submit review.</p>}
      {query.data.status === "failed" && <button disabled={action.busy} onClick={() => action.run(() => post(`/jobs/${id}/retry`, {}))}>Retry job</button>}
    </>}
  </div>;
}

export function Media({ assetId, renderId, seek = 0, kind = "video" }) {
  const query = useApi(assetId ? `/assets/${assetId}/delivery` : renderId ? `/exports/${renderId}/delivery` : null);
  const player = useRef(null);
  useEffect(() => { if (player.current && seek !== null) player.current.currentTime = seek; }, [seek]);
  if (!assetId && !renderId) return null;
  return <div className="media"><Status query={query} />
    {query.data && (kind === "image" ? <img src={query.data.url} alt="Uploaded asset" /> :
      kind === "audio" ? <audio controls src={query.data.url} /> :
      <video ref={player} controls playsInline src={query.data.url} onLoadedMetadata={() => { if (player.current) player.current.currentTime = seek || 0; }} />)}
    {query.data && <a href={query.data.url} target="_blank" rel="noreferrer">Open / download media</a>}
    <button onClick={() => query.refetch()} className="secondary">Refresh playback link</button>
  </div>;
}

export function time(ms) { return `${(ms / 1000).toFixed(1)}s`; }

