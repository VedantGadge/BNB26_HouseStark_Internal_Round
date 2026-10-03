from dataclasses import dataclass


@dataclass(frozen=True)
class UploadedAssetReference:
    """Provider-neutral media identity; a delivery URL is not an asset identity."""

    asset_id: str
    public_id: str
    resource_type: str
    version: str


class CloudinaryStorage:
    """Reserved seam for controlled upload signatures and authenticated source delivery."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str) -> None:
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
