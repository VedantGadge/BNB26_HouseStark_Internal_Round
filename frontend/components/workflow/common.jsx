"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, post } from "@/lib/api";
import { CheckCircle, Clock, WarningCircle } from "@phosphor-icons/react";
import { humanize } from "@/lib/creator.mjs";

export function useApi(path, poll = false) {
  return useQuery({
    queryKey: [path],
    queryFn: () => apiFetch(path),
    enabled: Boolean(path),
    refetchInterval: poll
      ? (query) =>
          path?.startsWith("/jobs/") &&
          ["completed", "failed", "waiting_review"].includes(
            query.state.data?.status,
          )
            ? false
            : 4000
      : false,
  });
}

export function useAction() {
  const cache = useQueryClient();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function run(action) {
    setError("");
    setBusy(true);
    try {
      const result = await action();
      await cache.invalidateQueries();
      return result;
    } catch (failure) {
      setError(failure.message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  return { error, busy, run };
}

export function Status({ query, error }) {
  return (
    <>
      {query?.isPending && query?.fetchStatus !== "idle" && (
        <div className="status-loading" role="status">
          <span className="loading-label">Loading workspace…</span>
          <span className="skeleton-line" aria-hidden="true" />
          <span className="skeleton-line" aria-hidden="true" />
          <span className="skeleton-line" aria-hidden="true" />
        </div>
      )}
      {(error || query?.error?.message) && (
        <div role="alert" className="notice error">
          <p>{error || query.error.message}</p>
          {query?.isError && (
            <button className="secondary" onClick={() => query.refetch()}>
              Try again
            </button>
          )}
        </div>
      )}
    </>
  );
}

export function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export function Job({ id, onDone }) {
  const query = useApi(id ? `/jobs/${id}` : null, true);
  const action = useAction();
  const notified = useRef(null);
  useEffect(() => {
    if (query.data?.status === "completed" && notified.current !== id) {
      notified.current = id;
      onDone?.(query.data);
    }
  }, [query.data, id, onDone]);
  if (!id) return null;
  return (
    <div className="job" aria-live="polite">
      <Status query={query} error={action.error} />
      {query.data && (
        <>
          <div className="job-top">
            {query.data.status === "completed" ? (
              <CheckCircle size={21} weight="light" className="success" />
            ) : query.data.status === "failed" ? (
              <WarningCircle size={21} weight="light" />
            ) : (
              <Clock size={21} weight="light" />
            )}
            <strong>
              {humanize(
                query.data.type || query.data.job_type || "Background task",
              )}{" "}
              · {humanize(query.data.status)}
            </strong>
          </div>
          <p className="muted">{humanize(query.data.stage)}</p>
          {query.data.error && <p className="error">{query.data.error}</p>}
          {query.data.status === "waiting_review" && (
            <p>
              Drafts are ready. Open a clip, save your changes, then submit
              review.
            </p>
          )}
          {query.data.status === "failed" && (
            <button
              disabled={action.busy}
              onClick={() => action.run(() => post(`/jobs/${id}/retry`, {}))}
            >
              Retry job
            </button>
          )}
        </>
      )}
    </div>
  );
}

export function Media({ assetId, renderId, seek = 0, kind = "video" }) {
  const path = assetId
    ? `/assets/${assetId}/delivery`
    : renderId
      ? `/exports/${renderId}/delivery`
      : null;
  const query = useQuery({
    queryKey: [path],
    queryFn: () => apiFetch(path),
    enabled: Boolean(path),
    refetchInterval: 240000,
  });
  const [playbackError, setPlaybackError] = useState("");
  const player = useRef(null);
  useEffect(() => {
    if (player.current && seek !== null) player.current.currentTime = seek;
  }, [seek]);
  if (!assetId && !renderId) return null;
  return (
    <div className="media">
      <Status query={query} error={playbackError} />
      {query.data &&
        (kind === "image" ? (
          <img src={query.data.url} alt="Uploaded asset" />
        ) : kind === "audio" ? (
          <audio controls src={query.data.url} />
        ) : (
          <video
            ref={player}
            controls
            playsInline
            preload="metadata"
            src={query.data.url}
            onError={() =>
              setPlaybackError(
                "The media could not play. Refresh the signed playback link and try again.",
              )
            }
            onLoadedMetadata={() => {
              setPlaybackError("");
              if (player.current) player.current.currentTime = seek || 0;
            }}
          />
        ))}
      {query.data && (
        <a href={query.data.url} target="_blank" rel="noreferrer">
          Open / download media
        </a>
      )}
      <button
        type="button"
        onClick={() => query.refetch()}
        className="secondary"
      >
        Refresh playback link
      </button>
    </div>
  );
}

export function time(ms) {
  return `${(ms / 1000).toFixed(1)}s`;
}
