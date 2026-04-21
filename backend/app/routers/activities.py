from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity, Segment, SegmentEffort

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("/{athlete_id}")
def list_activities(
    athlete_id: int,
    sport_type: str | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Activity).filter(Activity.athlete_id == athlete_id)
    if sport_type:
        q = q.filter(Activity.sport_type == sport_type)
    q = q.order_by(Activity.start_date.desc())
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [_activity_dict(a) for a in items],
    }


@router.get("/{athlete_id}/pace-over-time")
def pace_over_time(
    athlete_id: int,
    sport_type: str = "Run",
    db: Session = Depends(get_db),
):
    """Returns date + pace (min/km) for all activities of a given sport type."""
    activities = (
        db.query(Activity)
        .filter(
            Activity.athlete_id == athlete_id,
            Activity.sport_type == sport_type,
            Activity.average_speed > 0,
            Activity.distance > 0,
        )
        .order_by(Activity.start_date)
        .all()
    )
    return [
        {
            "date": a.start_date.isoformat() if a.start_date else None,
            "pace_min_per_km": round((1000 / a.average_speed) / 60, 2) if a.average_speed else None,
            "distance_km": round(a.distance / 1000, 2),
            "name": a.name,
            "id": a.id,
        }
        for a in activities
    ]


@router.get("/{athlete_id}/weekly-volume")
def weekly_volume(
    athlete_id: int,
    sport_type: str = "Run",
    db: Session = Depends(get_db),
):
    """Weekly distance totals (km) grouped by ISO week."""
    rows = (
        db.query(
            func.date_trunc("week", Activity.start_date).label("week"),
            func.sum(Activity.distance).label("total_distance"),
            func.sum(Activity.moving_time).label("total_time"),
            func.count(Activity.id).label("count"),
        )
        .filter(
            Activity.athlete_id == athlete_id,
            Activity.sport_type == sport_type,
        )
        .group_by("week")
        .order_by("week")
        .all()
    )
    return [
        {
            "week": row.week.isoformat() if row.week else None,
            "distance_km": round(row.total_distance / 1000, 2) if row.total_distance else 0,
            "total_time_seconds": row.total_time or 0,
            "count": row.count,
        }
        for row in rows
    ]


@router.get("/{athlete_id}/segments")
def athlete_segments(athlete_id: int, db: Session = Depends(get_db)):
    """All segments the athlete has efforts on, with PR time."""
    rows = (
        db.query(
            Segment.id,
            Segment.name,
            Segment.distance,
            Segment.average_grade,
            func.min(SegmentEffort.elapsed_time).label("pr_seconds"),
            func.count(SegmentEffort.id).label("effort_count"),
        )
        .join(SegmentEffort, SegmentEffort.segment_id == Segment.id)
        .filter(SegmentEffort.athlete_id == athlete_id)
        .group_by(Segment.id, Segment.name, Segment.distance, Segment.average_grade)
        .order_by(func.count(SegmentEffort.id).desc())
        .all()
    )
    return [
        {
            "segment_id": r.id,
            "name": r.name,
            "distance_m": r.distance,
            "average_grade": r.average_grade,
            "pr_seconds": r.pr_seconds,
            "effort_count": r.effort_count,
        }
        for r in rows
    ]


@router.get("/{athlete_id}/segments/{segment_id}/history")
def segment_history(athlete_id: int, segment_id: int, db: Session = Depends(get_db)):
    """All efforts on a segment over time."""
    efforts = (
        db.query(SegmentEffort)
        .filter(
            SegmentEffort.athlete_id == athlete_id,
            SegmentEffort.segment_id == segment_id,
        )
        .order_by(SegmentEffort.start_date)
        .all()
    )
    return [
        {
            "date": e.start_date.isoformat() if e.start_date else None,
            "elapsed_time": e.elapsed_time,
            "moving_time": e.moving_time,
            "average_heartrate": e.average_heartrate,
            "pr_rank": e.pr_rank,
            "activity_id": e.activity_id,
        }
        for e in efforts
    ]


def _activity_dict(a: Activity) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "sport_type": a.sport_type,
        "start_date": a.start_date.isoformat() if a.start_date else None,
        "distance_km": round(a.distance / 1000, 2) if a.distance else None,
        "moving_time": a.moving_time,
        "average_speed": a.average_speed,
        "pace_min_per_km": round((1000 / a.average_speed) / 60, 2) if a.average_speed else None,
        "average_heartrate": a.average_heartrate,
        "total_elevation_gain": a.total_elevation_gain,
        "average_watts": a.average_watts,
        "suffer_score": a.suffer_score,
    }
