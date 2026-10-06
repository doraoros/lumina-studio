from __future__ import annotations

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import ROOT
from app.db import init_db
from app.service import (
    create_upload_event,
    event_payload,
    get_job,
    latest_event,
    person_cover_path,
    person_photos,
    photo_path,
    save_upload,
    start_demo,
    start_upload,
)

app = FastAPI(title="Lumina")
init_db()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/demo")
def demo_state() -> dict:
    try:
        event = latest_event()
    except Exception:
        event = None
    return {"event": event}


@app.post("/api/demo/run")
def demo_run() -> dict:
    try:
        job_id = start_demo()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/api/events/{event_id}")
def event_detail(event_id: int) -> dict:
    try:
        return event_payload(event_id)
    except KeyError as exc:
        raise HTTPException(404, "Event not found") from exc


@app.get("/api/photos/{photo_id}/image")
def photo_image(photo_id: int) -> FileResponse:
    try:
        return FileResponse(photo_path(photo_id))
    except KeyError as exc:
        raise HTTPException(404, "Photo not found") from exc


@app.get("/api/people/{person_id}/photos")
def person_frames(person_id: int) -> dict:
    try:
        return {"photos": person_photos(person_id)}
    except KeyError as exc:
        raise HTTPException(404, "Person not found") from exc


@app.get("/api/people/{person_id}/cover")
def person_cover(person_id: int) -> FileResponse:
    try:
        return FileResponse(person_cover_path(person_id))
    except KeyError as exc:
        raise HTTPException(404, "Person not found") from exc


class UploadOpen(BaseModel):
    name: str = "Own upload"


@app.post("/api/uploads")
def open_upload(payload: UploadOpen = Body(default_factory=UploadOpen)) -> dict:
    return {"event_id": create_upload_event(payload.name)}


@app.post("/api/events/{event_id}/files")
async def add_files(event_id: int, files: list[UploadFile] = File(...)) -> dict:
    saved = 0
    for item in files:
        content = await item.read()
        if not content:
            continue
        save_upload(event_id, item.filename or "foto.jpg", content)
        saved += 1
    return {"saved": saved}


@app.post("/api/events/{event_id}/process")
def process_upload(event_id: int) -> dict:
    try:
        job_id = start_upload(event_id)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"job_id": job_id}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
