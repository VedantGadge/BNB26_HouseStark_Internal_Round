"""Real signed-upload smoke check through the durable worker.

Start tests/browser_fixture.py with CREATORAI_QA_LIVE=1 first. This script
refuses ordinary app servers and never bypasses production authentication.
QA records remain available until the isolated fixture server shuts down.
Supply only media you are authorized to send to Cloudinary and Groq.
"""

import argparse
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--api-url", default="http://127.0.0.1:8011")
    parser.add_argument(
        "--analyze-with-groq",
        action="store_true",
        help="Compatibility option; the video worker always analyzes with Groq.",
    )
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_file() or source.suffix.lower() != ".mp4":
        parser.error("source must be an existing authorized MP4 file")
    if source.stat().st_size > 100_000_000:
        parser.error("source exceeds the 100 MB upload limit")
    with httpx.Client(base_url=args.api_url.rstrip("/"), timeout=300) as client:
        response = client.get("/qa-info")
        response.raise_for_status()
        info = response.json()
        if (
            info.get("provider_data") != "LIVE PROVIDERS"
            or info.get("database") != "ISOLATED POSTGRESQL SCHEMA"
        ):
            raise RuntimeError("Use the explicitly enabled isolated live-provider QA server")

        def request(method, path, **kwargs):
            response = client.request(method, "/v1" + path, **kwargs)
            response.raise_for_status()
            return response.json()

        project = request(
            "POST",
            "/projects",
            json={
                "name": "[QA live] Signed ingestion smoke check",
                "brief": "Labelled integration test, not real creator content.",
                "target_platforms": ["instagram", "youtube"],
            },
        )
        upload = request(
            "POST",
            f"/projects/{project['id']}/assets/upload-session",
            json={
                "filename": source.name,
                "content_type": "video/mp4",
                "kind": "video",
                "byte_size": source.stat().st_size,
                "tags": ["labelled-qa", "live-smoke"],
            },
        )
        form = {
            key: str(upload[key]).lower() if isinstance(upload[key], bool) else str(upload[key])
            for key in ("api_key", "timestamp", "signature", "public_id", "overwrite")
        }
        form["type"] = upload["delivery_type"]
        with source.open("rb") as handle:
            response = httpx.post(
                upload["upload_url"],
                data=form,
                files={"file": (source.name, handle, "video/mp4")},
                timeout=300,
            )
        response.raise_for_status()
        provider = response.json()
        request(
            "POST",
            f"/assets/{upload['asset_id']}/complete",
            json={
                "provider_asset_id": provider["asset_id"],
                "provider_version": str(provider["version"]),
            },
        )
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            workflow = request("GET", f"/projects/{project['id']}/workflow")
            job = next(j for j in workflow["jobs"] if j["type"] == "asset_ingestion")
            if job["status"] == "failed":
                raise RuntimeError(job["error"])
            if job["status"] == "completed":
                break
            time.sleep(2)
        else:
            raise TimeoutError("Durable ingestion did not finish within 15 minutes")
        analysis = request("GET", f"/assets/{upload['asset_id']}/analysis")
        assert analysis["processing_status"] == "ready"
        assert analysis["visual_observations"]
        print("signed_upload=passed completion_verification=passed durable_ingestion=passed")
        print(
            f"groq_transcript_segments={len(analysis['transcript_segments'])} "
            f"groq_visual_observations={len(analysis['visual_observations'])}"
        )
        print(f"isolated_qa_project={project['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
