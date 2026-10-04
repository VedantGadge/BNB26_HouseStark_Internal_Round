"use client";

import Link from "next/link";
import { useState } from "react";
import { apiFetch, post } from "@/lib/api";
import { Field, Status, useAction, useApi } from "./common";

export function YouTubeMetrics({ projectId, publications }) {
  const account = useApi("/me/youtube");
  const action = useAction();
  const [synced, setSynced] = useState(null);

  return (
    <section className="form-section">
      <h2>YouTube performance</h2>
      <p className="muted">
        Connect your channel to import views, likes, comments and shares for
        your published videos and Shorts.
      </p>
      <Status query={account} error={action.error} />
      {account.data && (
        <>
          {account.data.connected && (
            <p>Connected to {account.data.channel_title}.</p>
          )}
          {!account.data.configured && (
            <p>
              YouTube connection is currently unavailable. You can enter metrics
              below.
            </p>
          )}
          <div className="actions">
            <button
              disabled={action.busy || !account.data.configured}
              onClick={() =>
                action.run(async () => {
                  const result = await post("/me/youtube/authorize", {
                    project_id: projectId,
                  });
                  sessionStorage.setItem(
                    "creatorai-youtube-state",
                    result.state,
                  );
                  window.location.assign(result.authorization_url);
                })
              }
            >
              {account.data.connected ? "Reconnect YouTube" : "Connect YouTube"}
            </button>
            {account.data.connected && (
              <button
                className="secondary"
                disabled={action.busy}
                onClick={() =>
                  action.run(async () => {
                    await apiFetch("/me/youtube", { method: "DELETE" });
                    setSynced(null);
                  })
                }
              >
                Disconnect YouTube
              </button>
            )}
          </div>
          {publications.length ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                const fields = new FormData(event.currentTarget);
                setSynced(null);
                action.run(async () => {
                  const result = await post(
                    `/publications/${fields.get("publication")}/performance/youtube`,
                    { reporting_window_days: Number(fields.get("window")) },
                  );
                  setSynced(result);
                });
              }}
            >
              <Field label="Published YouTube video">
                <select name="publication">
                  {publications.map((publication) => (
                    <option key={publication.id} value={publication.id}>
                      {publication.supporting_copy.title || "YouTube video"}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Import up to this many days since publication">
                <input
                  name="window"
                  type="number"
                  min="1"
                  max="365"
                  defaultValue="7"
                  required
                />
              </Field>
              <p className="muted">
                Save the video’s YouTube URL in Publish first. Reports use
                YouTube’s Pacific calendar days and may lag behind live counts.
                The saved window reflects the data available when you sync.
              </p>
              <button
                disabled={
                  action.busy ||
                  !account.data.connected ||
                  !account.data.configured
                }
              >
                {action.busy ? "Working…" : "Sync YouTube metrics"}
              </button>
            </form>
          ) : (
            <p>
              <Link href={`/projects/${projectId}/publish`}>
                Confirm a YouTube publication
              </Link>{" "}
              to sync its performance.
            </p>
          )}
          {synced && (
            <p role="status">
              Imported {synced.views} views, {synced.likes} likes,{" "}
              {synced.comments} comments and {synced.shares} shares across{" "}
              {synced.reporting_window_days} YouTube calendar days.
            </p>
          )}
        </>
      )}
    </section>
  );
}
