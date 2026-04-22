from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255))
    firstname: Mapped[str | None] = mapped_column(String(255))
    lastname: Mapped[str | None] = mapped_column(String(255))
    profile_medium: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    activities: Mapped[list["Activity"]] = relationship(back_populates="athlete")
    sync_logs: Mapped[list["SyncLog"]] = relationship(back_populates="athlete")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("athletes.id"))
    name: Mapped[str | None] = mapped_column(Text)
    sport_type: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    distance: Mapped[float | None] = mapped_column(Float)          # metres
    moving_time: Mapped[int | None] = mapped_column(Integer)       # seconds
    elapsed_time: Mapped[int | None] = mapped_column(Integer)      # seconds
    total_elevation_gain: Mapped[float | None] = mapped_column(Float)
    average_speed: Mapped[float | None] = mapped_column(Float)     # m/s
    max_speed: Mapped[float | None] = mapped_column(Float)
    average_heartrate: Mapped[float | None] = mapped_column(Float)
    max_heartrate: Mapped[float | None] = mapped_column(Float)
    average_watts: Mapped[float | None] = mapped_column(Float)
    average_cadence: Mapped[float | None] = mapped_column(Float)
    suffer_score: Mapped[int | None] = mapped_column(Integer)
    kudos_count: Mapped[int | None] = mapped_column(Integer)
    achievement_count: Mapped[int | None] = mapped_column(Integer)
    map_summary_polyline: Mapped[str | None] = mapped_column(Text)
    map_polyline: Mapped[str | None] = mapped_column(Text)  # full-resolution
    start_latlng_lat: Mapped[float | None] = mapped_column(Float)
    start_latlng_lng: Mapped[float | None] = mapped_column(Float)
    trainer: Mapped[bool] = mapped_column(Boolean, default=False)
    commute: Mapped[bool] = mapped_column(Boolean, default=False)
    gear_id: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    athlete: Mapped["Athlete"] = relationship(back_populates="activities")
    segment_efforts: Mapped[list["SegmentEffort"]] = relationship(back_populates="activity")
    laps: Mapped[list["Lap"]] = relationship(back_populates="activity")
    best_efforts: Mapped[list["BestEffort"]] = relationship(back_populates="activity")


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    activity_type: Mapped[str | None] = mapped_column(String(100))
    distance: Mapped[float | None] = mapped_column(Float)
    average_grade: Mapped[float | None] = mapped_column(Float)
    maximum_grade: Mapped[float | None] = mapped_column(Float)
    elevation_high: Mapped[float | None] = mapped_column(Float)
    elevation_low: Mapped[float | None] = mapped_column(Float)
    city: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(255))
    climb_category: Mapped[int | None] = mapped_column(Integer)
    start_latlng_lat: Mapped[float | None] = mapped_column(Float)
    start_latlng_lng: Mapped[float | None] = mapped_column(Float)
    end_latlng_lat: Mapped[float | None] = mapped_column(Float)
    end_latlng_lng: Mapped[float | None] = mapped_column(Float)

    efforts: Mapped[list["SegmentEffort"]] = relationship(back_populates="segment")


class SegmentEffort(Base):
    __tablename__ = "segment_efforts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activity_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("activities.id"))
    athlete_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("athletes.id"))
    segment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("segments.id"))
    name: Mapped[str | None] = mapped_column(Text)
    elapsed_time: Mapped[int | None] = mapped_column(Integer)
    moving_time: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    distance: Mapped[float | None] = mapped_column(Float)
    average_watts: Mapped[float | None] = mapped_column(Float)
    average_heartrate: Mapped[float | None] = mapped_column(Float)
    pr_rank: Mapped[int | None] = mapped_column(Integer)
    kom_rank: Mapped[int | None] = mapped_column(Integer)

    activity: Mapped["Activity"] = relationship(back_populates="segment_efforts")
    segment: Mapped["Segment"] = relationship(back_populates="efforts")


class Lap(Base):
    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activity_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("activities.id"))
    name: Mapped[str | None] = mapped_column(String(255))
    lap_index: Mapped[int | None] = mapped_column(Integer)
    elapsed_time: Mapped[int | None] = mapped_column(Integer)
    moving_time: Mapped[int | None] = mapped_column(Integer)
    distance: Mapped[float | None] = mapped_column(Float)
    average_speed: Mapped[float | None] = mapped_column(Float)
    max_speed: Mapped[float | None] = mapped_column(Float)
    average_heartrate: Mapped[float | None] = mapped_column(Float)
    average_watts: Mapped[float | None] = mapped_column(Float)
    average_cadence: Mapped[float | None] = mapped_column(Float)
    total_elevation_gain: Mapped[float | None] = mapped_column(Float)

    activity: Mapped["Activity"] = relationship(back_populates="laps")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("athletes.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    activities_synced: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="running")  # running | done | error
    error: Mapped[str | None] = mapped_column(Text)

    athlete: Mapped["Athlete"] = relationship(back_populates="sync_logs")


class BestEffort(Base):
    __tablename__ = "best_efforts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activity_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("activities.id"))
    athlete_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("athletes.id"))
    name: Mapped[str | None] = mapped_column(String(50))
    distance: Mapped[float | None] = mapped_column(Float)       # metres
    elapsed_time: Mapped[int | None] = mapped_column(Integer)   # seconds
    moving_time: Mapped[int | None] = mapped_column(Integer)    # seconds
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    pr_rank: Mapped[int | None] = mapped_column(Integer)

    activity: Mapped["Activity"] = relationship(back_populates="best_efforts")
