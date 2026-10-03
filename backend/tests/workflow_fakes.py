"""External provider fixtures only; media probing and rendering use real FFmpeg."""

import json
import shutil
import subprocess
from pathlib import Path

from app.features.assets.storage import UploadedAssetReference
from app.features.footage_analysis.probe import probe_media
from app.features.footage_analysis.transcription import TranscriptSegmentResult
from app.features.footage_analysis.vision import VisualObservationResult
from app.features.script_creation.provider import ProviderResult

SCRIPT = {
    "hooks": [{"id": "hook-1", "text": "A better camera setup"}],
    "selected_hook_id": "hook-1",
    "sections": [
        {
            "id": "section-1",
            "position": 1,
            "heading": "Camera",
            "text": "Camera lens lighting setup",
        },
        {
            "id": "section-2",
            "position": 2,
            "heading": "Sound",
            "text": "Microphone voice audio recording",
        },
        {
            "id": "section-3",
            "position": 3,
            "heading": "Visual demonstration",
            "text": "Red product package demonstration",
        },
        {
            "id": "section-4",
            "position": 4,
            "heading": "Unmatched",
            "text": "Astronaut spaceship Jupiter launch",
        },
    ],
    "title": "Camera setup guide",
    "description": "A practical production guide",
    "call_to_action": "Save this guide",
    "production_notes": ["Show the product package"],
}


def make_source(path: Path):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "35",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )


class Storage:
    def __init__(self, root, delivery_base="https://example.test"):
        self.root, self.delivery_base = root, delivery_base
        self.source = root / "source.mp4"
        make_source(self.source)
        self.uploads = {}

    def create_upload_session(self, *, public_id, resource_type):
        return {
            "cloud_name": "fixture-cloud",
            "api_key": "fixture-public",
            "resource_type": resource_type,
            "upload_url": "https://example.test/upload",
            "public_id": public_id,
            "delivery_type": "authenticated",
            "overwrite": False,
            "timestamp": 1700000000,
            "signature": "fixture-signature",
        }

    def get_asset_metadata(self, *, public_id, resource_type):
        if public_id in self.uploads:
            reference = self.uploads[public_id]["reference"]
            return {
                "asset_id": reference.asset_id,
                "public_id": public_id,
                "resource_type": "video",
                "version": reference.version,
                "type": "authenticated",
            }
        if "/renders/" in public_id:
            raise RuntimeError("No uploaded render yet")
        return {
            "asset_id": "provider-source",
            "public_id": public_id,
            "resource_type": resource_type,
            "version": 1,
            "type": "authenticated",
            "format": "mp4",
            "bytes": self.source.stat().st_size,
            "width": 640,
            "height": 360,
            "duration": 35,
        }

    def download_original_to_path(self, *, destination, **kwargs):
        shutil.copyfile(self.source, destination)

    def upload_authenticated_video_from_path(self, *, source_path, public_id):
        path = self.root / f"render-{len(self.uploads)}.mp4"
        shutil.copyfile(source_path, path)
        reference = UploadedAssetReference(f"render-{len(self.uploads)}", public_id, "video", "1")
        self.uploads[public_id] = {"path": path, "probe": probe_media(path), "reference": reference}
        return reference

    def delivery_url(self, *, public_id, **kwargs):
        if public_id in self.uploads:
            return f"{self.delivery_base}/fixture-media/{self.uploads[public_id]['path'].name}"
        return f"{self.delivery_base}/fixture-media/source.mp4"


class Transcriber:
    def transcribe(self, source_path):
        return [
            TranscriptSegmentResult(1000, 3000, "Camera lens lighting setup"),
            TranscriptSegmentResult(12000, 14000, "Microphone voice audio recording"),
        ]


class Vision:
    def inspect(self, source_path):
        return [
            VisualObservationResult(
                25000, 25000, ["source_frame_ms:25000"], "Red product package demonstration", 0.95
            )
        ]


class Alignment:
    def generate_json(self, *, user_prompt, **kwargs):
        evidence = json.loads(user_prompt)["evidence"]
        return ProviderResult(
            {
                "matches": [
                    {
                        "section_id": f"section-{index + 1}",
                        "evidence_id": item["id"],
                        "status": "matched",
                        "confidence": 0.95,
                    }
                    for index, item in enumerate(evidence)
                ]
                + [
                    {
                        "section_id": "section-4",
                        "evidence_id": None,
                        "status": "unmatched",
                        "confidence": 0,
                    }
                ]
            },
            "fixture-model",
            "fixture",
            100,
            100,
        )
