from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from app.config import DEMO_TARGET, SHOOT, SOURCES, USER_AGENT

SOURCE_VERSION = "4"
SHOOT_VERSION = 4
UNSPLASH_IDS = [
    "1519741497674-611481863552",
    "1511285560929-80b456fea0bc",
    "1522673607200-164d1b6ce486",
    "1519225421980-715cb0215aed",
    "1520854221256-17451cc331bf",
    "1583939003579-730e3918a45a",
    "1591604466107-ec97de577aff",
    "1606800052052-a08af7148866",
    "1537633552985-df8429e8048b",
    "1544078751-58fee2d8a03b",
    "1529636798458-92182e662485",
    "1465495976277-4387d4b0b4c6",
    "1532712938310-34cb3982ef74",
    "1520854221256-17451cc331bf",
    "1545232979-8bf68ee9b1af",
    "1529634597503-139d42d1e877",
    "1515934751635-c81c6bc9a2d8",
    "1460978812857-470ed1c77af0",
    "1478146896981-b80fe463b330",
    "1550005809-91ad75fb315f",
    "1509927083803-4bd519298ac4",
    "1524504388940-b1c1722653e1",
    "1494790108377-be9c29b29330",
    "1507003211169-0a1dd7228f2d",
    "1534528741775-53994a69daeb",
    "1524502397800-2eeaad7c3fe5",
    "1488426862026-3ee34a7d66df",
    "1529626455594-4ff0802cfb7e",
    "1531123897727-8f129e1688ce",
    "1502823403499-6ccfcf4fb453",
]
COMMONS_CATEGORIES = [
    "Category:Brides",
    "Category:Brides and grooms",
    "Category:Wedding ceremonies",
    "Category:Wedding photography",
    "Category:Wedding receptions",
    "Category:Grooms",
]
TITLE_BLOCK = (
    "painting",
    "oil",
    "canvas",
    "illustration",
    "drawing",
    "engraving",
    "fresco",
    "miniature",
    "tapestry",
    "sculpture",
    "statue",
    "icon",
    "sketch",
    "watercolor",
    "poster",
)


def _request(url: str, timeout: int = 40) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def _candidate_urls() -> list[str]:
    urls = [
        f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=1000&q=75"
        for photo_id in UNSPLASH_IDS
    ]
    for category in COMMONS_CATEGORIES:
        params = urllib.parse.urlencode(
            {
                "action": "query",
                "format": "json",
                "generator": "categorymembers",
                "gcmtitle": category,
                "gcmtype": "file",
                "gcmlimit": "40",
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "iiurlwidth": "1000",
            }
        )
        try:
            payload = json.loads(_request(f"https://commons.wikimedia.org/w/api.php?{params}").decode("utf-8"))
        except Exception:
            continue
        for page in payload.get("query", {}).get("pages", {}).values():
            title = (page.get("title") or "").lower()
            if any(word in title for word in TITLE_BLOCK):
                continue
            info = (page.get("imageinfo") or [{}])[0]
            thumb = info.get("thumburl") or ""
            mime = info.get("mime", "")
            if thumb and mime in {"image/jpeg", "image/png", "image/webp"}:
                urls.append(thumb)
    return urls


def _usable_portrait(img: np.ndarray, vision) -> bool:
    from app.pipeline import _exposure, _sharpness

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if _sharpness(gray) < 0.42 or _exposure(gray) < 0.48:
        return False
    faces = vision.inspect(img)
    return any(max(face["box"][2], face["box"][3]) >= 48 for face in faces)


def ensure_sources(progress=None, limit: int = 56) -> list[Path]:
    from app.pipeline import Vision

    SOURCES.mkdir(parents=True, exist_ok=True)
    marker = SOURCES / "version.txt"
    if not marker.exists() or marker.read_text(encoding="utf-8").strip() != SOURCE_VERSION:
        for old in SOURCES.glob("base_*.jpg"):
            old.unlink()
        marker.write_text(SOURCE_VERSION, encoding="utf-8")

    existing = sorted(SOURCES.glob("base_*.jpg"))
    if len(existing) >= limit:
        return existing

    vision = Vision()
    seen: set[str] = set()
    known = {hashlib.md5(path.read_bytes()).hexdigest() for path in existing}
    saved = len(existing)
    for url in _candidate_urls():
        if saved >= limit or url in seen:
            continue
        seen.add(url)
        dest = SOURCES / f"base_{saved:03d}.jpg"
        try:
            raw = _request(url)
            digest = hashlib.md5(raw).hexdigest()
            if digest in known:
                continue
            arr = np.frombuffer(raw, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None or min(img.shape[:2]) < 280:
                continue
            img = _resize_max(img, 960)
            if not _usable_portrait(img, vision):
                continue
            known.add(digest)
            cv2.imwrite(str(dest), img, [cv2.IMWRITE_JPEG_QUALITY, 86])
            saved += 1
            if progress:
                progress(saved, limit, "surse")
        except Exception:
            continue
    found = sorted(SOURCES.glob("base_*.jpg"))
    if len(found) < min(8, limit):
        raise RuntimeError("Could not download enough photographs with clear faces.")
    return found


def _resize_max(img: np.ndarray, max_side: int) -> np.ndarray:
    height, width = img.shape[:2]
    scale = max_side / max(height, width)
    if scale >= 1:
        return img
    size = (int(width * scale), int(height * scale))
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA)


def _crop_frac(img: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
    height, width = img.shape[:2]
    xa, xb = int(width * x0), int(width * x1)
    ya, yb = int(height * y0), int(height * y1)
    xa, ya = max(0, xa), max(0, ya)
    xb, yb = min(width, xb), min(height, yb)
    if xb - xa < 40 or yb - ya < 40:
        return img
    return img[ya:yb, xa:xb]


def _good_variant(img: np.ndarray, index: int) -> np.ndarray:
    crops = [
        (0.0, 0.0, 1.0, 1.0),
        (0.07, 0.06, 0.93, 0.94),
        (0.0, 0.04, 0.80, 0.96),
        (0.16, 0.0, 1.0, 0.82),
        (0.10, 0.12, 0.88, 0.90),
    ]
    x0, y0, x1, y1 = crops[index % len(crops)]
    out = _crop_frac(img, x0, y0, x1, y1)
    if index == 4:
        out = np.clip(out.astype(np.float32) * 1.05 + 4, 0, 255).astype(np.uint8)
    return _resize_max(out, 840)


def _bad_variant(img: np.ndarray, kind: str) -> np.ndarray:
    frame = _resize_max(img, 840)
    if kind == "blur":
        height, width = frame.shape[:2]
        tiny = cv2.resize(frame, (max(8, width // 28), max(8, height // 28)), interpolation=cv2.INTER_AREA)
        soft = cv2.resize(tiny, (width, height), interpolation=cv2.INTER_LINEAR)
        return cv2.GaussianBlur(soft, (31, 31), 0)
    if kind == "dark":
        return np.clip(frame.astype(np.float32) * 0.16, 0, 255).astype(np.uint8)
    blown = frame.astype(np.float32) * 3.1 + 40
    return np.clip(blown, 0, 255).astype(np.uint8)


def _write_dup(img: np.ndarray, dest: Path, rng: np.random.Generator) -> None:
    noise = rng.normal(0, 1.0, img.shape).astype(np.float32)
    noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", noisy, [cv2.IMWRITE_JPEG_QUALITY, 78])
    if not ok:
        raise RuntimeError(f"Could not write {dest.name}")
    dest.write_bytes(buf.tobytes())


def build_shoot(bases: list[Path], progress=None, target: int = DEMO_TARGET) -> list[dict]:
    """Build a shoot of `target` frames from real photographs.

    Each source becomes a scene: a few good compositions, near-identical
    bursts, and failed frames (motion, exposure). Labels are for validation
    only; the culling decision does not read them.
    """
    SHOOT.mkdir(parents=True, exist_ok=True)
    manifest_path = SHOOT / "manifest.json"
    meta_path = SHOOT / "meta.json"
    existing = sorted(SHOOT.glob("frame_*.jpg"))
    if meta_path.exists() and manifest_path.exists() and len(existing) >= target:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("version") == SHOOT_VERSION and meta.get("count") == target:
            return json.loads(manifest_path.read_text(encoding="utf-8"))

    for old in SHOOT.glob("frame_*.jpg"):
        old.unlink()

    rng = np.random.default_rng(7)
    n = len(bases)
    goods_per = 5
    bads_per = 8
    base_block = goods_per + bads_per
    if n * (base_block + 1) > target:
        raise RuntimeError("The target frame count is too small for the number of sources.")
    dups_per = (target // n) - base_block
    # The remainder up to `target` is added as duplicates on the first scenes.
    planned = n * (goods_per + dups_per + bads_per)
    extra_dups = target - planned

    bad_cycle = ["blur", "blur", "dark", "dark", "blow", "blur", "dark", "blow"]
    manifest: list[dict] = []
    images = []
    for path in bases:
        img = cv2.imread(str(path))
        if img is None:
            raise RuntimeError(f"Could not read source: {path.name}")
        images.append(img)

    for scene_index, img in enumerate(images):
        scene = f"{scene_index:03d}"
        good_paths: list[tuple[np.ndarray, str]] = []
        for shot in range(goods_per):
            variant = _good_variant(img, shot)
            filename = f"frame_{len(manifest):04d}.jpg"
            dest = SHOOT / filename
            cv2.imwrite(str(dest), variant, [cv2.IMWRITE_JPEG_QUALITY, 82])
            manifest.append(
                {
                    "filename": filename,
                    "scene": scene,
                    "role": "good",
                    "shot": shot,
                }
            )
            good_paths.append((variant, filename))

        dup_budget = dups_per + (1 if scene_index < extra_dups else 0)
        for dup_index in range(dup_budget):
            variant, _parent = good_paths[dup_index % len(good_paths)]
            filename = f"frame_{len(manifest):04d}.jpg"
            _write_dup(variant, SHOOT / filename, rng)
            manifest.append(
                {
                    "filename": filename,
                    "scene": scene,
                    "role": "dup",
                    "shot": dup_index % len(good_paths),
                }
            )

        for bad_index in range(bads_per):
            kind = bad_cycle[bad_index % len(bad_cycle)]
            filename = f"frame_{len(manifest):04d}.jpg"
            dest = SHOOT / filename
            cv2.imwrite(
                str(dest),
                _bad_variant(img, kind),
                [cv2.IMWRITE_JPEG_QUALITY, 80],
            )
            manifest.append(
                {
                    "filename": filename,
                    "scene": scene,
                    "role": "bad",
                    "shot": bad_index,
                    "bad_kind": kind,
                }
            )
        if progress and (scene_index % 2 == 0 or scene_index == n - 1):
            progress(len(manifest), target, "generare")

    if len(manifest) != target:
        raise RuntimeError(f"The set has {len(manifest)} frames, expected {target}.")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    meta_path.write_text(
        json.dumps({"version": SHOOT_VERSION, "count": target}),
        encoding="utf-8",
    )
    return manifest
