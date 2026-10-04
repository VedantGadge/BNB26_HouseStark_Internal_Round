"""Read-only Google OAuth and YouTube Analytics requests."""

import re
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.config import Settings

SCOPES = (
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
)
PACIFIC = ZoneInfo("America/Los_Angeles")
METRICS = ("views", "likes", "comments", "shares")


def token_cipher(settings: Settings) -> Fernet:
    if not all(
        (
            settings.youtube_client_id,
            settings.youtube_client_secret,
            settings.youtube_token_encryption_key,
        )
    ):
        raise HTTPException(503, "YouTube connection is not configured on the server.")
    try:
        return Fernet(settings.youtube_token_encryption_key.get_secret_value().encode())
    except (ValueError, TypeError) as error:
        raise HTTPException(503, "YouTube token encryption is not configured correctly.") from error


def video_id_from_url(value: str | None) -> str:
    parsed = urlparse(value or "")
    parts = parsed.path.strip("/").split("/")
    video_id = ""
    if parsed.scheme == "https" and not parsed.username and not parsed.password:
        if parsed.hostname in {"youtu.be", "www.youtu.be"} and len(parts) == 1:
            video_id = parts[0]
        elif parsed.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
                video_id = parts[1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise HTTPException(422, "Save a valid YouTube video or Shorts URL in Publish first.")
    return video_id


class YouTubeProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cipher = token_cipher(settings)

    def encrypt(self, token: str) -> str:
        return self.cipher.encrypt(token.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self.cipher.decrypt(token.encode()).decode()
        except InvalidToken as error:
            raise HTTPException(409, "Reconnect YouTube to restore account access.") from error

    def _request(self, method, url, **kwargs):
        try:
            response = httpx.request(method, url, timeout=15, follow_redirects=False, **kwargs)
            body = response.json()
        except httpx.RequestError as error:
            raise HTTPException(503, "YouTube is unavailable. Try syncing again later.") from error
        except ValueError as error:
            raise HTTPException(502, "YouTube returned an invalid response.") from error
        if response.status_code == 401 or (
            isinstance(body, dict) and body.get("error") == "invalid_grant"
        ):
            raise HTTPException(409, "YouTube access expired or was revoked. Reconnect YouTube.")
        if response.status_code == 403:
            raise HTTPException(
                403,
                "YouTube access denied. Check API enablement and reconnect with both "
                "read-only permissions.",
            )
        if response.status_code == 429 or response.status_code >= 500:
            raise HTTPException(503, "YouTube is unavailable or rate limited. Try again later.")
        if not response.is_success or not isinstance(body, dict):
            raise HTTPException(502, "YouTube could not complete the request.")
        return body

    def exchange_code(self, code: str):
        result = self._request(
            "POST",
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": self.settings.youtube_client_id,
                "client_secret": self.settings.youtube_client_secret.get_secret_value(),
                "redirect_uri": self.settings.youtube_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if not set(SCOPES) <= set(result.get("scope", "").split()):
            raise HTTPException(409, "Allow both YouTube read-only permissions when connecting.")
        if not result.get("access_token") or not result.get("refresh_token"):
            raise HTTPException(409, "Reconnect YouTube and allow offline access.")
        return result

    def refresh_access(self, encrypted_refresh_token: str) -> str:
        result = self._request(
            "POST",
            "https://oauth2.googleapis.com/token",
            data={
                "refresh_token": self.decrypt(encrypted_refresh_token),
                "client_id": self.settings.youtube_client_id,
                "client_secret": self.settings.youtube_client_secret.get_secret_value(),
                "grant_type": "refresh_token",
            },
        )
        if not isinstance(result.get("access_token"), str) or not result["access_token"]:
            raise HTTPException(502, "YouTube returned an invalid access token.")
        return result["access_token"]

    def channel(self, access_token: str) -> dict:
        body = self._request(
            "GET",
            "https://www.googleapis.com/youtube/v3/channels",
            params={
                "part": "snippet",
                "mine": "true",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        items = body.get("items", [])
        if len(items) != 1:
            raise HTTPException(409, "Choose a Google account with a YouTube channel.")
        try:
            return {"id": items[0]["id"], "title": items[0]["snippet"]["title"]}
        except (KeyError, TypeError) as error:
            raise HTTPException(502, "YouTube returned invalid channel details.") from error

    def performance(self, access_token, channel_id, video_id, window_days):
        headers = {"Authorization": f"Bearer {access_token}"}
        body = self._request(
            "GET",
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet",
                "id": video_id,
            },
            headers=headers,
        )
        items = body.get("items", [])
        if not items:
            raise HTTPException(404, "The YouTube video was not found or is inaccessible.")
        try:
            snippet = items[0]["snippet"]
            if snippet["channelId"] != channel_id:
                raise HTTPException(409, "This video belongs to a different YouTube channel.")
            published = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
            if published.tzinfo is None:
                raise ValueError("missing timezone")
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(502, "YouTube returned invalid video details.") from error
        start = published.astimezone(PACIFIC).date()
        end = min(
            start + timedelta(days=window_days - 1),
            datetime.now(PACIFIC).date() - timedelta(days=1),
        )
        if end < start:
            raise HTTPException(409, "YouTube analytics are not available for this new video yet.")
        report = self._request(
            "GET",
            "https://youtubeanalytics.googleapis.com/v2/reports",
            params={
                "ids": f"channel=={channel_id}",
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "metrics": ",".join(METRICS),
                "dimensions": "day",
                "filters": f"video=={video_id}",
                "sort": "day",
                "maxResults": 365,
            },
            headers=headers,
        )
        rows = report.get("rows")
        if not rows:
            raise HTTPException(409, "YouTube has no available analytics for this video yet.")
        try:
            columns = [column["name"] for column in report["columnHeaders"]]
            if not {"day", *METRICS} <= set(columns) or len(set(columns)) != len(columns):
                raise ValueError("missing metrics")
            totals = dict.fromkeys(METRICS, 0)
            days = set()
            for row in rows:
                if len(row) != len(columns):
                    raise ValueError("invalid row")
                record = dict(zip(columns, row, strict=True))
                day = date.fromisoformat(record["day"])
                if not start <= day <= end or day in days:
                    raise ValueError("invalid reporting date")
                days.add(day)
                for metric in METRICS:
                    count = record[metric]
                    if (
                        isinstance(count, bool)
                        or not isinstance(count, int | float)
                        or count < 0
                        or int(count) != count
                    ):
                        raise ValueError("invalid count")
                    totals[metric] += int(count)
            # Google truncates reports to the latest day with all requested metrics.
            # Preserve that actual window, rather than labelling partial data as a full window.
            available_end = max(days)
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise HTTPException(502, "YouTube returned incomplete or invalid analytics.") from error
        return {
            **totals,
            "observed_at": datetime.now(UTC),
            "reporting_window_days": (available_end - start).days + 1,
            "reporting_basis": "youtube_calendar_days",
            "source": f"YouTube Analytics API · {start} to {available_end} (Pacific)",
        }

    def revoke(self, encrypted_refresh_token):
        try:
            httpx.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": self.decrypt(encrypted_refresh_token)},
                timeout=15,
            )
        except (httpx.RequestError, HTTPException):
            # Local credentials are still removed; the creator can also revoke in Google.
            pass
