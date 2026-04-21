import time
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app import strava
from app.database import get_db
from app.models import Activity, Athlete, Lap, Segment, SegmentEffort, SyncLog

router = APIRouter(prefix="/sync", tags=["sync"])


def _upsert_activity(db: Session, athlete_id: int, detail: dict):
    activity_id = detail["id"]
    activity = db.get(Activity, activity_id)
    if activity is None:
        activity = Activity(id=activity_id, athlete_id=athlete_id)
        db.add(activity)

    activity.name = detail.get("name")
    activity.sport_type = detail.get("sport_type") or detail.get("type")
    activity.start_date = datetime.fromisoformat(detail["start_date"].replace("Z", "+00:00")) if detail.get("start_date") else None
    activity.distance = detail.get("distance")
    activity.moving_time = detail.get("moving_time")
    activity.elapsed_time = detail.get("elapsed_time")
    activity.total_elevation_gain = detail.get("total_elevation_gain")
    activity.average_speed = detail.get("average_speed")
    activity.max_speed = detail.get("max_speed")
    activity.average_heartrate = detail.get("average_heartrate")
    activity.max_heartrate = detail.get("max_heartrate")
    activity.average_watts = detail.get("average_watts")
    activity.average_cadence = detail.get("average_cadence")
    activity.suffer_score = detail.get("suffer_score")
    activity.kudos_count = detail.get("kudos_count")
    activity.achievement_count = detail.get("achievement_count")
    activity.map_summary_polyline = (detail.get("map") or {}).get("summary_polyline")
    activity.trainer = detail.get("trainer", False)
    activity.commute = detail.get("commute", False)
    activity.gear_id = detail.get("gear_id")
    activity.description = detail.get("description")

    # Segment efforts (included when fetching detail with include_all_efforts=True)
    for effort_data in detail.get("segment_efforts", []):
        seg_data = effort_data.get("segment", {})
        segment = db.get(Segment, seg_data["id"])
        if segment is None:
            segment = Segment(id=seg_data["id"])
            db.add(segment)
        segment.name = seg_data.get("name")
        segment.activity_type = seg_data.get("activity_type")
        segment.distance = seg_data.get("distance")
        segment.average_grade = seg_data.get("average_grade")
        segment.maximum_grade = seg_data.get("maximum_grade")
        segment.elevation_high = seg_data.get("elevation_high")
        segment.elevation_low = seg_data.get("elevation_low")
        segment.city = seg_data.get("city")
        segment.country = seg_data.get("country")
        segment.climb_category = seg_data.get("climb_category")

        effort = db.get(SegmentEffort, effort_data["id"])
        if effort is None:
            effort = SegmentEffort(id=effort_data["id"])
            db.add(effort)
        effort.activity_id = activity_id
        effort.athlete_id = athlete_id
        effort.segment_id = seg_data["id"]
        effort.name = effort_data.get("name")
        effort.elapsed_time = effort_data.get("elapsed_time")
        effort.moving_time = effort_data.get("moving_time")
        effort.start_date = datetime.fromisoformat(effort_data["start_date"].replace("Z", "+00:00")) if effort_data.get("start_date") else None
        effort.distance = effort_data.get("distance")
        effort.average_watts = effort_data.get("average_watts")
        effort.average_heartrate = effort_data.get("average_heartrate")
        effort.pr_rank = effort_data.get("pr_rank")
        effort.kom_rank = effort_data.get("kom_rank")

    # Laps
    for lap_data in detail.get("laps", []):
        lap = db.get(Lap, lap_data["id"])
        if lap is None:
            lap = Lap(id=lap_data["id"], activity_id=activity_id)
            db.add(lap)
        lap.name = lap_data.get("name")
        lap.lap_index = lap_data.get("lap_index")
        lap.elapsed_time = lap_data.get("elapsed_time")
        lap.moving_time = lap_data.get("moving_time")
        lap.distance = lap_data.get("distance")
        lap.average_speed = lap_data.get("average_speed")
        lap.max_speed = lap_data.get("max_speed")
        lap.average_heartrate = lap_data.get("average_heartrate")
        lap.average_watts = lap_data.get("average_watts")
        lap.average_cadence = lap_data.get("average_cadence")
        lap.total_elevation_gain = lap_data.get("total_elevation_gain")


def _run_sync(athlete_id: int, sync_log_id: int):
    """Background task: paginate all activities then fetch details."""
    db = next(get_db())
    try:
        athlete = db.get(Athlete, athlete_id)
        sync_log = db.get(SyncLog, sync_log_id)
        token = strava.get_valid_token(athlete)
        db.commit()

        synced = 0
        page = 1
        while True:
            summaries = strava.get_activities(token, page=page)
            if not summaries:
                break

            for summary in summaries:
                # Refresh token before each detail call if needed
                token = strava.get_valid_token(athlete)
                detail = strava.get_activity_detail(token, summary["id"])
                _upsert_activity(db, athlete_id, detail)
                synced += 1
                db.commit()
                # Respect rate limits: ~1 req/s is well within 100/15min
                time.sleep(0.5)

            page += 1

        sync_log.status = "done"
        sync_log.activities_synced = synced
        sync_log.finished_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        sync_log = db.get(SyncLog, sync_log_id)
        if sync_log:
            sync_log.status = "error"
            sync_log.error = str(e)
            sync_log.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@router.post("/{athlete_id}")
def trigger_sync(athlete_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    # Block if a sync is already running
    running = db.query(SyncLog).filter_by(athlete_id=athlete_id, status="running").first()
    if running:
        raise HTTPException(status_code=409, detail="Sync already in progress")

    sync_log = SyncLog(athlete_id=athlete_id)
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    background_tasks.add_task(_run_sync, athlete_id, sync_log.id)
    return {"sync_log_id": sync_log.id, "status": "running"}


@router.get("/{athlete_id}/status")
def sync_status(athlete_id: int, db: Session = Depends(get_db)):
    log = (
        db.query(SyncLog)
        .filter_by(athlete_id=athlete_id)
        .order_by(SyncLog.started_at.desc())
        .first()
    )
    if not log:
        return {"status": "never_synced"}
    return {
        "sync_log_id": log.id,
        "status": log.status,
        "activities_synced": log.activities_synced,
        "started_at": log.started_at,
        "finished_at": log.finished_at,
        "error": log.error,
    }
