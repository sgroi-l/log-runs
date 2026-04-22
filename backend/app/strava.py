import time
from datetime import datetime, timezone

import httpx

from app.config import settings

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"

def _sleep_until_next_window(reason: str) -> None:
    now = datetime.now(timezone.utc)
    seconds_into_window = (now.minute % 15) * 60 + now.second
    sleep_for = 900 - seconds_into_window + 10
    resume_at = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    print(f"[strava] rate limit: {reason} — sleeping {sleep_for}s, resuming ~{resume_at}", flush=True)
    time.sleep(sleep_for)
    print("[strava] resuming after rate limit sleep", flush=True)


def _throttle(response: httpx.Response) -> None:
    usage_header = response.headers.get("X-RateLimit-Usage", "")
    limit_header = response.headers.get("X-RateLimit-Limit", "")
    if not usage_header or not limit_header:
        return
    short_used = int(usage_header.split(",")[0])
    short_limit = int(limit_header.split(",")[0])
    if short_used >= short_limit - 5:
        _sleep_until_next_window(f"usage {short_used}/{short_limit}")


def _get(url: str, **kwargs) -> httpx.Response:
    """GET with automatic retry on 429 and transient timeouts."""
    for attempt in range(3):
        try:
            resp = httpx.get(url, **kwargs)
        except (httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
            if attempt == 2:
                raise
            wait = 30 * (attempt + 1)
            print(f"[strava] timeout ({exc}), retrying in {wait}s (attempt {attempt + 1}/3)", flush=True)
            time.sleep(wait)
            continue
        if resp.status_code == 429:
            _sleep_until_next_window("got 429")
            continue
        resp.raise_for_status()
        _throttle(resp)
        return resp
    raise RuntimeError("unreachable")


STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


def get_auth_url(redirect_uri: str) -> str:
    params = {
        "client_id": settings.strava_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "read,activity:read_all",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{STRAVA_AUTH_URL}?{query}"


def exchange_code(code: str) -> dict:
    resp = httpx.post(STRAVA_TOKEN_URL, data={
        "client_id": settings.strava_client_id,
        "client_secret": settings.strava_client_secret,
        "code": code,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    resp = httpx.post(STRAVA_TOKEN_URL, data={
        "client_id": settings.strava_client_id,
        "client_secret": settings.strava_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()


def get_valid_token(athlete) -> str:
    if athlete.token_expires_at < int(time.time()) + 60:
        data = refresh_access_token(athlete.refresh_token)
        athlete.access_token = data["access_token"]
        athlete.refresh_token = data["refresh_token"]
        athlete.token_expires_at = data["expires_at"]
    return athlete.access_token


def get_activities(access_token: str, page: int = 1, per_page: int = 100, after: int | None = None) -> list[dict]:
    params: dict = {"page": page, "per_page": per_page}
    if after is not None:
        params["after"] = after
    return _get(
        f"{STRAVA_API_BASE}/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
        timeout=30,
    ).json()


def get_activity_detail(access_token: str, activity_id: int) -> dict:
    return _get(
        f"{STRAVA_API_BASE}/activities/{activity_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"include_all_efforts": True},
        timeout=30,
    ).json()
