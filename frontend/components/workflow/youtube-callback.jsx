"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { post } from "@/lib/api";

export function YouTubeCallback() {
  const router = useRouter();
  const started = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const params = new URLSearchParams(window.location.search);
    window.history.replaceState(null, "", window.location.pathname);
    async function complete() {
      const expected = sessionStorage.getItem("creatorai-youtube-state");
      sessionStorage.removeItem("creatorai-youtube-state");
      if (!expected || params.get("state") !== expected) {
        throw new Error(
          "This YouTube connection was not started in this browser. Connect again.",
        );
      }
      if (params.has("error")) {
        throw new Error(
          "YouTube connection was cancelled. You can try again from Insights.",
        );
      }
      if (!params.get("code"))
        throw new Error("YouTube did not return an authorization code.");
      const result = await post("/me/youtube/callback", {
        state: expected,
        code: params.get("code"),
      });
      router.replace(`/projects/${result.project_id}/insights`);
    }
    complete().catch((failure) => setError(failure.message));
  }, [router]);

  return (
    <main id="main-content" className="workspace">
      <h1>Connect YouTube</h1>
      {error ? (
        <>
          <p role="alert">{error}</p>
          <Link href="/projects">Return to projects</Link>
        </>
      ) : (
        <p role="status">Connecting your YouTube channel…</p>
      )}
    </main>
  );
}
