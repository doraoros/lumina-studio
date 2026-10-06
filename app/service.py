from __future__ import annotations

import json
import shutil
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2

from app.config import DATA, DEMO_TARGET, SHOOT, UPLOADS
from app.dataset import build_shoot, ensure_sources
from app.db import init_db, session
from app.economics import analyze as analyze_economics
from app.pipeline import (
    Frame,
    Vision,
    analyze_frame,
    build_album,
    cluster_people,
    mark_duplicates,
    summarize,
    validation,
)

JOBS: dict[str, dict] = {}
LOCK = threading.Lock()
_VISION: Vision | None = None
_VISION_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _job(job_id: str, **fields) -> None:
    with LOCK:
        JOBS[job_id].update(fields)
        job = JOBS[job_id]
    print(f"{job.get('phase')}: {job.get('detail')} ({float(job.get('progress') or 0):.0%})", flush=True)


def get_job(job_id: str) -> dict | None:
    with LOCK:
        job = JOBS.get(job_id)
        return dict(job) if job else None


def _vision() -> Vision:
    global _VISION
    with _VISION_LOCK:
        if _VISION is None:
            _VISION = Vision()
        return _VISION


def running() -> bool:
    with LOCK:
        return any(job["status"] == "running" for job in JOBS.values())


def start_demo() -> str:
    if running():
        raise RuntimeError("An analysis is already running.")
    job_id = uuid.uuid4().hex[:12]
    with LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "status": "running",
            "phase": "Preparing",
            "progress": 0.0,
            "detail": "Opening sources",
            "event_id": None,
            "error": None,
        }
    threading.Thread(target=_run_demo, args=(job_id,), daemon=True).start()
    return job_id


def start_upload(event_id: int) -> str:
    if running():
        raise RuntimeError("An analysis is already running.")
    job_id = uuid.uuid4().hex[:12]
    with LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "status": "running",
            "phase": "Analysis",
            "progress": 0.02,
            "detail": "Reading the uploaded photos",
            "event_id": event_id,
            "error": None,
        }
    threading.Thread(target=_run_upload, args=(job_id, event_id), daemon=True).start()
    return job_id


def _run_demo(job_id: str) -> None:
    started = time.perf_counter()
    try:
        init_db()

        def on_sources(done: int, total: int, _phase: str) -> None:
            _job(
                job_id,
                phase="Source photos",
                progress=0.12 * done / max(total, 1),
                detail=f"{done} sources downloaded",
            )

        _job(job_id, phase="Source photos", detail="Searching for wedding photographs")
        bases = ensure_sources(on_sources)

        def on_build(done: int, total: int, _phase: str) -> None:
            _job(
                job_id,
                phase="3,000-frame shoot",
                progress=0.12 + 0.28 * done / max(total, 1),
                detail=f"{done} / {total} frames prepared",
            )

        manifest = build_shoot(bases, on_build, DEMO_TARGET)
        frames = [
            Frame(
                filename=item["filename"],
                path=SHOOT / item["filename"],
                scene=item["scene"],
                role=item["role"],
            )
            for item in manifest
        ]
        event_id = _process(
            job_id,
            frames,
            name="Demo wedding",
            kind="demo",
            started=started,
            root=SHOOT,
        )
        _job(
            job_id,
            status="done",
            phase="Done",
            progress=1,
            detail="The album is ready",
            event_id=event_id,
        )
    except Exception as exc:
        traceback.print_exc()
        _job(job_id, status="error", phase="Error", error=str(exc), detail=str(exc))


def _run_upload(job_id: str, event_id: int) -> None:
    started = time.perf_counter()
    try:
        folder = UPLOADS / str(event_id)
        paths = sorted(
            path
            for path in folder.iterdir()
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
        if not paths:
            raise RuntimeError("There are no photos to analyze.")
        frames = [
            Frame(filename=path.name, path=path, scene=f"{index // 8:03d}", role=None)
            for index, path in enumerate(paths)
        ]
        _process(
            job_id,
            frames,
            name="Own upload",
            kind="upload",
            started=started,
            root=folder,
            event_id=event_id,
        )
        _job(
            job_id,
            status="done",
            phase="Done",
            progress=1,
            detail="The album is ready",
            event_id=event_id,
        )
    except Exception as exc:
        traceback.print_exc()
        _job(job_id, status="error", phase="Error", error=str(exc), detail=str(exc))


def _process(
    job_id: str,
    frames: list[Frame],
    name: str,
    kind: str,
    started: float,
    root: Path,
    event_id: int | None = None,
) -> int:
    total = len(frames)
    _job(job_id, phase="Quality", progress=0.42, detail=f"0 / {total}")
    for index, frame in enumerate(frames, start=1):
        analyze_frame(frame)
        if index % 40 == 0 or index == total:
            _job(
                job_id,
                phase="Quality",
                progress=0.42 + 0.22 * index / total,
                detail=f"{index} / {total} frames measured",
            )

    _job(job_id, phase="Duplicates", progress=0.66, detail="Comparing bursts")
    mark_duplicates(frames)

    _job(job_id, phase="People", progress=0.68, detail="Loading YuNet and SFace")
    vision = _vision()
    keepers = [frame for frame in frames if frame.status == "kept"]
    _job(job_id, phase="People", progress=0.70, detail=f"0 / {len(keepers)}")
    for index, frame in enumerate(keepers, start=1):
        analyze_frame(frame, vision, with_faces=True)
        if index % 20 == 0 or index == len(keepers):
            _job(
                job_id,
                phase="People",
                progress=0.70 + 0.18 * index / max(len(keepers), 1),
                detail=f"{index} / {len(keepers)} frames with faces",
            )

    _job(job_id, phase="Album", progress=0.90, detail="Composing the selection")
    build_album(frames)
    people = cluster_people(frames, vision.recognizer is not None)
    summary = summarize(frames, len(people))
    summary["validation"] = validation(frames)
    elapsed = time.perf_counter() - started
    summary["process_seconds"] = round(elapsed, 1)
    print(
        "Lumina:",
        {key: summary[key] for key in ("photo_count", "rejected", "duplicates", "unique_kept", "album_count", "people_count")},
        summary["validation"],
        flush=True,
    )
    summary["economics"] = analyze_economics(total, elapsed)
    summary["source_note"] = (
        "The demo shoot starts from real wedding photographs. "
        "Bursts, motion blur, and bad exposures are derived from them "
        "so there is a 3,000-frame set to cull."
        if kind == "demo"
        else "Photos uploaded by the user."
    )

    _job(job_id, phase="Registry", progress=0.95, detail="Writing the database")
    return _persist(name, kind, frames, people, summary, root, event_id)


def _persist(
    name: str,
    kind: str,
    frames: list[Frame],
    people: list[dict],
    summary: dict,
    root: Path,
    event_id: int | None,
) -> int:
    covers = DATA / "covers"
    covers.mkdir(parents=True, exist_ok=True)
    by_name = {frame.filename: frame for frame in frames}

    with session() as conn:
        if event_id is None:
            cur = conn.execute(
                """
                INSERT INTO events (name, kind, created_at, photo_count, process_seconds, summary_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    kind,
                    _now(),
                    len(frames),
                    summary["process_seconds"],
                    json.dumps(summary, ensure_ascii=False),
                ),
            )
            event_id = int(cur.lastrowid)
        else:
            conn.execute("DELETE FROM faces WHERE event_id = ?", (event_id,))
            conn.execute("DELETE FROM people WHERE event_id = ?", (event_id,))
            conn.execute("DELETE FROM photos WHERE event_id = ?", (event_id,))
            conn.execute(
                """
                UPDATE events
                SET name = ?, photo_count = ?, process_seconds = ?, summary_json = ?
                WHERE id = ?
                """,
                (
                    name,
                    len(frames),
                    summary["process_seconds"],
                    json.dumps(summary, ensure_ascii=False),
                    event_id,
                ),
            )

        conn.executemany(
            """
            INSERT INTO photos (
                event_id, filename, rel_path, scene, role, sharpness, exposure, score,
                face_count, status, reason, section, album_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    event_id,
                    frame.filename,
                    frame.path.resolve().relative_to(DATA.resolve()).as_posix(),
                    frame.scene,
                    frame.role,
                    round(frame.sharpness, 4),
                    round(frame.exposure, 4),
                    round(frame.score, 4),
                    frame.face_count,
                    frame.status,
                    frame.reason,
                    frame.section,
                    frame.album_order,
                )
                for frame in frames
            ],
        )
        id_rows = conn.execute(
            "SELECT id, filename FROM photos WHERE event_id = ?",
            (event_id,),
        ).fetchall()
        ids = {row["filename"]: row["id"] for row in id_rows}
        dup_updates = [
            (ids[frame.duplicate_of], ids[frame.filename])
            for frame in frames
            if frame.duplicate_of and frame.duplicate_of in ids and frame.filename in ids
        ]
        conn.executemany(
            "UPDATE photos SET duplicate_of = ? WHERE id = ?",
            dup_updates,
        )

        for index, person in enumerate(people, start=1):
            cover_rel = _write_cover(event_id, index, person, by_name, covers)
            cur = conn.execute(
                """
                INSERT INTO people (event_id, label, photo_count, cover_path)
                VALUES (?, ?, ?, ?)
                """,
                (event_id, f"Person {index}", len(person["filenames"]), cover_rel),
            )
            person_id = int(cur.lastrowid)
            face_rows = []
            seen_photo = set()
            for member in person["members"]:
                photo_id = ids.get(member["filename"])
                if photo_id is None or photo_id in seen_photo:
                    continue
                seen_photo.add(photo_id)
                x, y, w, h = member["box"]
                face_rows.append((event_id, photo_id, person_id, x, y, w, h))
            conn.executemany(
                """
                INSERT INTO faces (event_id, photo_id, person_id, x, y, w, h)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                face_rows,
            )
    return event_id


def _write_cover(event_id: int, index: int, person: dict, by_name: dict, covers: Path) -> str | None:
    best = None
    for member in person["members"]:
        frame = by_name.get(member["filename"])
        if frame is None:
            continue
        x, y, w, h = member["box"]
        rank = (frame.score, w * h)
        if best is None or rank > best[0]:
            best = (rank, frame, member["box"])
    if best is None:
        return None
    _rank, frame, (x, y, w, h) = best
    image = cv2.imread(str(frame.path))
    if image is None:
        return None
    height, width = image.shape[:2]
    margin = int(0.55 * max(w, h))
    xa, ya = max(0, x - margin), max(0, y - margin)
    xb, yb = min(width, x + w + margin), min(height, y + h + margin)
    crop = image[ya:yb, xa:xb]
    if crop.size == 0:
        return None
    dest = covers / f"event{event_id}_person{index}.jpg"
    cv2.imwrite(str(dest), crop, [cv2.IMWRITE_JPEG_QUALITY, 86])
    return dest.resolve().relative_to(DATA.resolve()).as_posix()


def create_upload_event(name: str) -> int:
    init_db()
    with session() as conn:
        cur = conn.execute(
            """
            INSERT INTO events (name, kind, created_at, photo_count)
            VALUES (?, 'upload', ?, 0)
            """,
            (name or "Own upload", _now()),
        )
        event_id = int(cur.lastrowid)
    folder = UPLOADS / str(event_id)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
    return event_id


def save_upload(event_id: int, filename: str, payload: bytes) -> None:
    folder = UPLOADS / str(event_id)
    folder.mkdir(parents=True, exist_ok=True)
    safe = Path(filename).name
    suffix = Path(safe).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        return
    target = folder / safe
    if target.exists():
        target = folder / f"{target.stem}_{uuid.uuid4().hex[:6]}{suffix}"
    target.write_bytes(payload)


def latest_event() -> dict | None:
    init_db()
    with session() as conn:
        row = conn.execute(
            """
            SELECT * FROM events
            WHERE summary_json IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return _event_payload(int(row["id"]))


def event_payload(event_id: int) -> dict:
    init_db()
    return _event_payload(event_id)


def _event_payload(event_id: int) -> dict:
    with session() as conn:
        event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if event is None:
            raise KeyError(event_id)
        summary = json.loads(event["summary_json"] or "{}")
        album = conn.execute(
            """
            SELECT id, filename, score, sharpness, exposure, section, scene, face_count
            FROM photos
            WHERE event_id = ? AND status = 'album'
            ORDER BY album_order
            """,
            (event_id,),
        ).fetchall()
        people = conn.execute(
            """
            SELECT id, label, photo_count, cover_path
            FROM people
            WHERE event_id = ?
            ORDER BY photo_count DESC, id
            LIMIT 18
            """,
            (event_id,),
        ).fetchall()
        rejected = conn.execute(
            """
            SELECT id, reason, score
            FROM photos
            WHERE event_id = ? AND status = 'rejected'
            ORDER BY score
            LIMIT 8
            """,
            (event_id,),
        ).fetchall()
        groups = conn.execute(
            """
            SELECT duplicate_of AS keep_id, COUNT(*) AS copies
            FROM photos
            WHERE event_id = ? AND status = 'duplicate' AND duplicate_of IS NOT NULL
            GROUP BY duplicate_of
            ORDER BY copies DESC
            LIMIT 4
            """,
            (event_id,),
        ).fetchall()
        duplicate_sets = []
        for group in groups:
            dups = conn.execute(
                """
                SELECT id FROM photos
                WHERE event_id = ? AND duplicate_of = ?
                ORDER BY id
                LIMIT 3
                """,
                (event_id, group["keep_id"]),
            ).fetchall()
            duplicate_sets.append(
                {
                    "keep_id": group["keep_id"],
                    "dup_ids": [row["id"] for row in dups],
                    "copies": group["copies"],
                }
            )
        counts = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM photos WHERE event_id = ?) AS photos,
                (SELECT COUNT(*) FROM people WHERE event_id = ?) AS people,
                (SELECT COUNT(*) FROM faces WHERE event_id = ?) AS faces
            """,
            (event_id, event_id, event_id),
        ).fetchone()
        preview = conn.execute(
            """
            SELECT id, filename, status, reason, ROUND(score, 3) AS score, face_count
            FROM photos
            WHERE event_id = ?
            ORDER BY id
            LIMIT 6
            """,
            (event_id,),
        ).fetchall()
        compare = conn.execute(
            """
            SELECT r.id AS before_id, k.id AS after_id
            FROM photos r
            JOIN photos k
              ON k.event_id = r.event_id
             AND k.scene = r.scene
             AND k.status = 'album'
            WHERE r.event_id = ?
              AND r.status = 'rejected'
              AND r.reason = 'Soft'
            ORDER BY k.score DESC, r.score
            LIMIT 1
            """,
            (event_id,),
        ).fetchone()
    return {
        "event": {
            "id": event["id"],
            "name": event["name"],
            "kind": event["kind"],
            "created_at": event["created_at"],
            "photo_count": event["photo_count"],
            "process_seconds": event["process_seconds"],
        },
        "summary": summary,
        "album": [dict(row) for row in album],
        "people": [
            {
                "id": row["id"],
                "label": row["label"],
                "photo_count": row["photo_count"],
                "cover_url": f"/api/people/{row['id']}/cover" if row["cover_path"] else None,
            }
            for row in people
        ],
        "samples": {
            "rejected": [dict(row) for row in rejected],
            "duplicates": duplicate_sets,
            "compare": dict(compare) if compare else None,
        },
        "registry": {
            "tables": [
                {"name": "events", "rows": 1},
                {"name": "photos", "rows": counts["photos"]},
                {"name": "people", "rows": counts["people"]},
                {"name": "faces", "rows": counts["faces"]},
            ],
            "preview": [dict(row) for row in preview],
        },
    }


def person_photos(person_id: int) -> list[dict]:
    with session() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.score, p.section, p.face_count
            FROM faces f
            JOIN photos p ON p.id = f.photo_id
            WHERE f.person_id = ?
            ORDER BY p.score DESC
            LIMIT 12
            """,
            (person_id,),
        ).fetchall()
    if not rows:
        raise KeyError(person_id)
    return [dict(row) for row in rows]


def photo_path(photo_id: int) -> Path:
    with session() as conn:
        row = conn.execute("SELECT rel_path FROM photos WHERE id = ?", (photo_id,)).fetchone()
    if row is None:
        raise KeyError(photo_id)
    return _safe_data_path(row["rel_path"])


def person_cover_path(person_id: int) -> Path:
    with session() as conn:
        row = conn.execute("SELECT cover_path FROM people WHERE id = ?", (person_id,)).fetchone()
    if row is None or not row["cover_path"]:
        raise KeyError(person_id)
    return _safe_data_path(row["cover_path"])


def _safe_data_path(rel_path: str) -> Path:
    path = (DATA / rel_path).resolve()
    if not path.is_relative_to(DATA.resolve()) or not path.exists():
        raise KeyError(rel_path)
    return path
