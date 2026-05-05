from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app import strava
from app.database import get_db
from app.models import Activity, Athlete, BestEffort, Lap, Segment, SegmentEffort

router = APIRouter(prefix="/activities", tags=["activities"])


def _rank_best_efforts(db: Session, athlete_id: int):
    """Return (rank_by_effort_id, total_by_name) for all of this athlete's best efforts,
    ranked by elapsed_time asc, ties sharing the min rank."""
    rows = (
        db.query(BestEffort.id, BestEffort.name, BestEffort.elapsed_time)
        .filter(BestEffort.athlete_id == athlete_id)
        .all()
    )
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r.name, []).append((r.elapsed_time or 10**12, r.id))
    rank_of: dict[int, int] = {}
    total_of: dict[str, int] = {}
    for name, items in groups.items():
        items.sort()
        prev_time = None
        prev_rank = 0
        for i, (t, eid) in enumerate(items, start=1):
            if t != prev_time:
                prev_rank = i
                prev_time = t
            rank_of[eid] = prev_rank
        total_of[name] = len(items)
    return rank_of, total_of


def _rank_segment_efforts(db: Session, athlete_id: int, segment_id: int | None = None):
    """Return (rank_by_effort_id, total_by_segment_id) ranked by elapsed_time asc."""
    q = db.query(SegmentEffort.id, SegmentEffort.segment_id, SegmentEffort.elapsed_time).filter(
        SegmentEffort.athlete_id == athlete_id
    )
    if segment_id is not None:
        q = q.filter(SegmentEffort.segment_id == segment_id)
    rows = q.all()
    groups: dict[int, list] = {}
    for r in rows:
        groups.setdefault(r.segment_id, []).append((r.elapsed_time or 10**12, r.id))
    rank_of: dict[int, int] = {}
    total_of: dict[int, int] = {}
    for sid, items in groups.items():
        items.sort()
        prev_time = None
        prev_rank = 0
        for i, (t, eid) in enumerate(items, start=1):
            if t != prev_time:
                prev_rank = i
                prev_time = t
            rank_of[eid] = prev_rank
        total_of[sid] = len(items)
    return rank_of, total_of


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


# Literal sub-routes must be registered before /{athlete_id}/{activity_id}
# so Starlette's registration-order matching doesn't swallow them.

@router.get("/{athlete_id}/pace-over-time")
def pace_over_time(
    athlete_id: int,
    sport_type: str = "Run",
    db: Session = Depends(get_db),
):
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
    rows = (
        db.query(
            Segment.id,
            Segment.name,
            Segment.distance,
            Segment.average_grade,
            func.min(SegmentEffort.elapsed_time).label("pr_seconds"),
            func.count(SegmentEffort.id).label("effort_count"),
            func.max(SegmentEffort.start_date).label("last_effort_date"),
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
            "last_effort_date": r.last_effort_date.isoformat() if r.last_effort_date else None,
        }
        for r in rows
    ]


@router.get("/{athlete_id}/segments/{segment_id}/history")
def segment_history(athlete_id: int, segment_id: int, db: Session = Depends(get_db)):
    efforts = (
        db.query(SegmentEffort)
        .filter(
            SegmentEffort.athlete_id == athlete_id,
            SegmentEffort.segment_id == segment_id,
        )
        .order_by(SegmentEffort.start_date)
        .all()
    )
    rank_of, total_of = _rank_segment_efforts(db, athlete_id, segment_id)
    total = total_of.get(segment_id, 0)
    return [
        {
            "date": e.start_date.isoformat() if e.start_date else None,
            "elapsed_time": e.elapsed_time,
            "moving_time": e.moving_time,
            "average_heartrate": e.average_heartrate,
            "pr_rank": rank_of.get(e.id),
            "total_efforts": total,
            "activity_id": e.activity_id,
        }
        for e in efforts
    ]


@router.get("/{athlete_id}/segments/{segment_id}/map")
def segment_map(athlete_id: int, segment_id: int, db: Session = Depends(get_db)):
    segment = db.get(Segment, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    if not segment.map_polyline:
        athlete = db.get(Athlete, athlete_id)
        if not athlete:
            raise HTTPException(status_code=404, detail="Athlete not found")
        token = strava.get_valid_token(athlete)
        data = strava.get_segment(token, segment_id)
        polyline = (data.get("map") or {}).get("polyline")
        if polyline:
            segment.map_polyline = polyline
            db.commit()
    return {
        "segment_id": segment_id,
        "polyline": segment.map_polyline,
        "start_latlng": (
            [segment.start_latlng_lat, segment.start_latlng_lng]
            if segment.start_latlng_lat is not None else None
        ),
        "end_latlng": (
            [segment.end_latlng_lat, segment.end_latlng_lng]
            if segment.end_latlng_lat is not None else None
        ),
    }


@router.get("/{athlete_id}/best-efforts/prs")
def best_effort_prs(athlete_id: int, db: Session = Depends(get_db)):
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
    efforts = (
        db.query(BestEffort)
        .filter(BestEffort.athlete_id == athlete_id, BestEffort.name == name)
        .order_by(BestEffort.start_date)
        .all()
    )
    rank_of, total_of = _rank_best_efforts(db, athlete_id)
    total = total_of.get(name, 0)
    return [
        {
            "date": e.start_date.isoformat() if e.start_date else None,
            "elapsed_time": e.elapsed_time,
            "pace_min_per_km": round((e.elapsed_time / 60) / (e.distance / 1000), 2) if e.distance and e.elapsed_time else None,
            "activity_id": e.activity_id,
            "pr_rank": rank_of.get(e.id),
            "total_efforts": total,
        }
        for e in efforts
    ]


@router.get("/{athlete_id}/{activity_id}")
def get_activity(athlete_id: int, activity_id: int, db: Session = Depends(get_db)):
    activity = (
        db.query(Activity)
        .options(
            joinedload(Activity.laps),
            joinedload(Activity.segment_efforts).joinedload(SegmentEffort.segment),
            joinedload(Activity.best_efforts),
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
    be_rank_of, be_total_of = _rank_best_efforts(db, athlete_id)
    seg_rank_of, seg_total_of = _rank_segment_efforts(db, athlete_id)
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
    base["best_efforts"] = [
        {
            "name": be.name,
            "distance_m": be.distance,
            "elapsed_time": be.elapsed_time,
            "moving_time": be.moving_time,
            "pace_min_per_km": round((be.elapsed_time / 60) / (be.distance / 1000), 2) if be.distance and be.elapsed_time else None,
            "pr_rank": be_rank_of.get(be.id),
            "total_efforts": be_total_of.get(be.name, 0),
        }
        for be in sorted(activity.best_efforts, key=lambda b: b.distance or 0)
    ]
    base["segment_efforts"] = [
        {
            "segment_id": e.segment_id,
            "name": e.name,
            "elapsed_time": e.elapsed_time,
            "distance_m": e.distance,
            "average_heartrate": e.average_heartrate,
            "pr_rank": seg_rank_of.get(e.id),
            "kom_rank": e.kom_rank,
            "total_efforts": seg_total_of.get(e.segment_id, 0),
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
