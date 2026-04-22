from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Activity, BestEffort, Lap, Segment, SegmentEffort

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


@router.get("/{athlete_id}/{activity_id}")
def get_activity(athlete_id: int, activity_id: int, db: Session = Depends(get_db)):
    activity = (
        db.query(Activity)
        .options(
            joinedload(Activity.laps),
            joinedload(Activity.segment_efforts).joinedload(SegmentEffort.segment),
        )
        .filter(Activity.id == activity_id, Activity.athlete_id == athlete_id)
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    base = _activity_dict(activity)
    base["map_polyline"] = activity.map_polyline
    base["map_summary_polyline"] = activity.map_summary_polyline
    base["start_latlng"] = (
        [activity.start_latlng_lat, activity.start_latlng_lng]
        if activity.start_latlng_lat is not None else None
    )
    base["description"] = activity.description
    base["laps"] = [
        {
            "lap_index": lap.lap_index,
            "name": lap.name,
            "distance_km": round(lap.distance / 1000, 2) if lap.distance else None,
            "moving_time": lap.moving_time,
            "average_speed": lap.average_speed,
            "pace_min_per_km": round((1000 / lap.average_speed) / 60, 2) if lap.average_speed else None,
            "average_heartrate": lap.average_heartrate,
            "total_elevation_gain": lap.total_elevation_gain,
        }
        for lap in sorted(activity.laps, key=lambda l: l.lap_index or 0)
    ]
    base["segment_efforts"] = [
        {
            "segment_id": e.segment_id,
            "name": e.name,
            "elapsed_time": e.elapsed_time,
            "distance_m": e.distance,
            "average_heartrate": e.average_heartrate,
            "pr_rank": e.pr_rank,
            "kom_rank": e.kom_rank,
            "segment_start_latlng": (
                [e.segment.start_latlng_lat, e.segment.start_latlng_lng]
                if e.segment and e.segment.start_latlng_lat is not None else None
            ),
            "segment_end_latlng": (
                [e.segment.end_latlng_lat, e.segment.end_latlng_lng]
                if e.segment and e.segment.end_latlng_lat is not None else None
            ),
        }
        for e in sorted(activity.segment_efforts, key=lambda e: e.start_date or activity.start_date)
    ]
    return base


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


@router.get("/{athlete_id}/best-efforts/prs")
def best_effort_prs(athlete_id: int, db: Session = Depends(get_db)):
    """Best (lowest elapsed_time) effort per distance name, with total effort count."""
    efforts = (
        db.query(BestEffort)
        .filter(BestEffort.athlete_id == athlete_id)
        .order_by(BestEffort.distance, BestEffort.elapsed_time)
        .all()
    )
    groups: dict[str, list] = {}
    for e in efforts:
        if e.name:
            groups.setdefault(e.name, []).append(e)

    result = []
    for name, group in sorted(groups.items(), key=lambda x: x[1][0].distance or 0):
        best = group[0]  # lowest elapsed_time first due to ORDER BY
        result.append({
            "name": best.name,
            "distance_m": best.distance,
            "elapsed_time": best.elapsed_time,
            "pace_min_per_km": round((best.elapsed_time / 60) / (best.distance / 1000), 2) if best.distance and best.elapsed_time else None,
            "activity_id": best.activity_id,
            "date": best.start_date.isoformat() if best.start_date else None,
            "pr_rank": best.pr_rank,
            "total_efforts": len(group),
        })
    return result


@router.get("/{athlete_id}/best-efforts/history")
def best_effort_history(
    athlete_id: int,
    name: str = Query(...),
    db: Session = Depends(get_db),
):
    """All efforts for a given distance name over time."""
    efforts = (
        db.query(BestEffort)
        .filter(BestEffort.athlete_id == athlete_id, BestEffort.name == name)
        .order_by(BestEffort.start_date)
        .all()
    )
    return [
        {
            "date": e.start_date.isoformat() if e.start_date else None,
            "elapsed_time": e.elapsed_time,
            "pace_min_per_km": round((e.elapsed_time / 60) / (e.distance / 1000), 2) if e.distance and e.elapsed_time else None,
            "activity_id": e.activity_id,
            "pr_rank": e.pr_rank,
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
        "max_heartrate": a.max_heartrate,
        "total_elevation_gain": a.total_elevation_gain,
        "average_watts": a.average_watts,
        "average_cadence": a.average_cadence,
        "suffer_score": a.suffer_score,
        "kudos_count": a.kudos_count,
        "trainer": a.trainer,
        "map_summary_polyline": a.map_summary_polyline,
    }
