import time

import httpx

from app.config import settings

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
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


def get_activities(access_token: str, page: int = 1, per_page: int = 100) -> list[dict]:
    resp = httpx.get(
        f"{STRAVA_API_BASE}/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"page": page, "per_page": per_page},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_activity_detail(access_token: str, activity_id: int) -> dict:
    resp = httpx.get(
        f"{STRAVA_API_BASE}/activities/{activity_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"include_all_efforts": True},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
