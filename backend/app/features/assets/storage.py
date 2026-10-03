import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cloudinary
import cloudinary.api
import cloudinary.utils
import httpx


@dataclass(frozen=True)
class UploadedAssetReference:
    """Provider-neutral media identity; a delivery URL is not an asset identity."""

    asset_id: str
    public_id: str
    resource_type: str
    version: str


class CloudinaryStorage:
    """Controlled signed uploads and server-side metadata verification."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str) -> None:
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

    def create_upload_session(self, *, public_id: str, resource_type: str) -> dict[str, str | int]:
        timestamp = int(time.time())
        # Cloudinary excludes a boolean False from its signature input. Keep the
        # literal string so the client can safely submit overwrite=false too.
        params_to_sign: dict[str, str | int] = {
            "public_id": public_id,
            "timestamp": timestamp,
            "type": "authenticated",
            "overwrite": "false",
        }
        signature = cloudinary.utils.api_sign_request(params_to_sign, self.api_secret)
        return {
            "cloud_name": self.cloud_name,
            "api_key": self.api_key,
            "resource_type": resource_type,
            "upload_url": (
                f"https://api.cloudinary.com/v1_1/{self.cloud_name}/{resource_type}/upload"
            ),
            "public_id": public_id,
            "delivery_type": "authenticated",
            "overwrite": False,
            "timestamp": timestamp,
            "signature": signature,
        }

    def get_asset_metadata(self, *, public_id: str, resource_type: str) -> dict[str, Any]:
        return cloudinary.api.resource(
            public_id,
            resource_type=resource_type,
            type="authenticated",
        )

    def download_original_to_path(
        self,
        *,
        public_id: str,
        resource_type: str,
        asset_format: str,
        destination: Path,
    ) -> None:
        """Download one authorized original into worker-local disposable storage."""

        download_url = cloudinary.utils.private_download_url(
            public_id,
            asset_format,
            resource_type=resource_type,
            type="authenticated",
            attachment=False,
        )
        with httpx.stream("GET", download_url, follow_redirects=True, timeout=60) as response:
            response.raise_for_status()
            with destination.open("wb") as output:
                for chunk in response.iter_bytes():
                    output.write(chunk)
