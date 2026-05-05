from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from app.config import settings
from app.database import engine, SessionLocal
from app.models import Base, SyncLog
from app.routers import activities, auth, sync

Base.metadata.create_all(bind=engine)

# Lightweight column additions for existing databases (no migrations framework).
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE segments ADD COLUMN IF NOT EXISTS map_polyline TEXT"))

# Clear any syncs that were running when the server last shut down
with SessionLocal() as db:
    db.query(SyncLog).filter_by(status="running").update({
        "status": "error",
        "error": "interrupted by server restart",
        "finished_at": datetime.utcnow(),
    })
    db.commit()

app = FastAPI(title="Log Runs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sync.router)
app.include_router(activities.router)


@app.get("/health")
def health():
    return {"status": "ok"}
