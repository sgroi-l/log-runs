from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import strava
from app.config import settings
from app.database import get_db
from app.models import Athlete

router = APIRouter(prefix="/auth", tags=["auth"])


def _redirect_uri(request: Request) -> str:
    return str(request.base_url) + "auth/callback"


@router.get("/login")
def login(request: Request):
    url = strava.get_auth_url(_redirect_uri(request))
    return RedirectResponse(url)


@router.get("/callback")
def callback(code: str, request: Request, db: Session = Depends(get_db)):
    try:
        data = strava.exchange_code(code)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to exchange Strava code")

    athlete_data = data["athlete"]
    athlete = db.get(Athlete, athlete_data["id"])
    if athlete is None:
        athlete = Athlete(id=athlete_data["id"])
        db.add(athlete)

    athlete.username = athlete_data.get("username")
    athlete.firstname = athlete_data.get("firstname")
    athlete.lastname = athlete_data.get("lastname")
    athlete.profile_medium = athlete_data.get("profile_medium")
    athlete.access_token = data["access_token"]
    athlete.refresh_token = data["refresh_token"]
    athlete.token_expires_at = data["expires_at"]
    db.commit()

    return RedirectResponse(f"{settings.frontend_url}?athlete_id={athlete.id}")


@router.get("/athlete/{athlete_id}")
def get_athlete(athlete_id: int, db: Session = Depends(get_db)):
    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return {
        "id": athlete.id,
        "username": athlete.username,
        "firstname": athlete.firstname,
        "lastname": athlete.lastname,
        "profile_medium": athlete.profile_medium,
    }
