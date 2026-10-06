from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from app.config import ALBUM_LIMIT, MODELS, USER_AGENT

YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
SFACE_URL = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
    "face_recognition_sface/face_recognition_sface_2021dec.onnx"
)

SHARP_MIN = 0.38
EXPOSURE_MIN = 0.50
DUP_HAMMING = 5
FACE_MATCH = 0.45
HIST_MATCH = 0.93

SECTIONS = ("Couple", "Portraits", "Guests", "Details")
SECTION_TARGETS = {"Couple": 56, "Portraits": 40, "Guests": 40, "Details": 24}


@dataclass
class Frame:
    filename: str
    path: Path
    scene: str
    role: str | None = None
    sharpness: float = 0.0
    exposure: float = 0.0
    score: float = 0.0
    digest: int = 0
    face_count: int = 0
    status: str = "kept"
    reason: str | None = None
    duplicate_of: str | None = None
    section: str | None = None
    album_order: int | None = None
    faces: list = field(default_factory=list)


def _download(url: str, dest: Path) -> None:
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 10_000:
        return
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as response:
        dest.write_bytes(response.read())


def ensure_models() -> tuple[Path, Path | None]:
    MODELS.mkdir(parents=True, exist_ok=True)
    yunet = MODELS / "face_detection_yunet_2023mar.onnx"
    sface = MODELS / "face_recognition_sface_2021dec.onnx"
    _download(YUNET_URL, yunet)
    try:
        _download(SFACE_URL, sface)
    except Exception:
        sface = None
    return yunet, sface if sface and sface.exists() else None


class Vision:
    def __init__(self) -> None:
        yunet, sface = ensure_models()
        self.detector = cv2.FaceDetectorYN.create(str(yunet), "", (320, 320), 0.68, 0.3, 12)
        self.recognizer = cv2.FaceRecognizerSF.create(str(sface), "") if sface else None

    def inspect(self, image: np.ndarray) -> list[dict]:
        height, width = image.shape[:2]
        scale = 720 / max(height, width)
        if scale < 1:
            work = cv2.resize(
                image,
                (int(width * scale), int(height * scale)),
                interpolation=cv2.INTER_AREA,
            )
        else:
            work = image
            scale = 1.0
        sh, sw = work.shape[:2]
        self.detector.setInputSize((sw, sh))
        _, found = self.detector.detect(work)
        faces = []
        if found is None:
            return faces
        for row in found[:8]:
            x, y, w, h = row[:4]
            if w < 24 or h < 24:
                continue
            ox = max(0, int(round(x / scale)))
            oy = max(0, int(round(y / scale)))
            ow = max(1, min(int(round(w / scale)), width - ox))
            oh = max(1, min(int(round(h / scale)), height - oy))
            crop = work[int(y) : int(y + h), int(x) : int(x + w)]
            if crop.size == 0:
                continue
            embedding = self._embed(work, row, crop)
            if embedding is None:
                continue
            faces.append({"box": (ox, oy, ow, oh), "embedding": embedding})
        return faces

    def _embed(self, image: np.ndarray, row: np.ndarray, crop: np.ndarray) -> np.ndarray | None:
        if self.recognizer is not None:
            try:
                aligned = self.recognizer.alignCrop(image, row)
                feature = self.recognizer.feature(aligned).flatten().astype(np.float32)
                norm = float(np.linalg.norm(feature))
                if norm == 0:
                    return None
                return feature / norm
            except cv2.error:
                return None
        hsv = cv2.cvtColor(cv2.resize(crop, (48, 48)), cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]).flatten()
        hist = hist.astype(np.float32)
        norm = float(np.linalg.norm(hist))
        if norm == 0:
            return None
        return hist / norm


def _sharpness(gray: np.ndarray) -> float:
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return float(variance / (variance + 90.0))


def _exposure(gray: np.ndarray) -> float:
    mean = float(gray.mean())
    if 98 <= mean <= 168:
        center = 1.0
    elif mean < 98:
        center = max(0.0, mean / 98.0)
    else:
        center = max(0.0, 1.0 - (mean - 168.0) / 75.0)
    clipped = float((gray < 8).mean() + (gray > 248).mean())
    return float(np.clip(center * (1.0 - min(clipped, 0.85)), 0.0, 1.0))


def _dhash(gray: np.ndarray) -> int:
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    diff = small[:, 1:] > small[:, :-1]
    bits = 0
    for bit in diff.flatten():
        bits = (bits << 1) | int(bit)
    return bits


def analyze_frame(frame: Frame, vision: Vision | None = None, with_faces: bool = False) -> None:
    image = cv2.imread(str(frame.path))
    if image is None:
        frame.status = "rejected"
        frame.reason = "Unreadable"
        frame.score = 0.0
        return
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    frame.sharpness = _sharpness(gray)
    frame.exposure = _exposure(gray)
    frame.digest = _dhash(gray)
    frame.score = 0.72 * frame.sharpness + 0.28 * frame.exposure
    if frame.sharpness < SHARP_MIN:
        frame.status = "rejected"
        frame.reason = "Soft"
    elif frame.exposure < EXPOSURE_MIN:
        frame.status = "rejected"
        frame.reason = "Poor exposure"
    else:
        frame.status = "kept"
        frame.reason = None
    if with_faces and vision is not None and frame.status == "kept":
        frame.faces = vision.inspect(image)
        frame.face_count = len(frame.faces)
        if frame.face_count:
            frame.score = 0.82 * frame.score + 0.18 * min(frame.face_count, 2) / 2


def mark_duplicates(frames: list[Frame]) -> None:
    scenes: dict[str, list[Frame]] = {}
    for frame in frames:
        if frame.status == "kept":
            scenes.setdefault(frame.scene, []).append(frame)

    for keepers in scenes.values():
        parent = list(range(len(keepers)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            a, b = find(left), find(right)
            if a == b:
                return
            if keepers[a].score >= keepers[b].score:
                parent[b] = a
            else:
                parent[a] = b

        for i in range(len(keepers)):
            for j in range(i + 1, len(keepers)):
                if (keepers[i].digest ^ keepers[j].digest).bit_count() <= DUP_HAMMING:
                    union(i, j)

        for index, frame in enumerate(keepers):
            root = find(index)
            if root == index:
                continue
            frame.status = "duplicate"
            frame.reason = "Duplicate"
            frame.duplicate_of = keepers[root].filename


def _section_for(face_count: int) -> str:
    if face_count >= 3:
        return "Guests"
    if face_count == 2:
        return "Couple"
    if face_count == 1:
        return "Portraits"
    return "Details"


def build_album(frames: list[Frame], limit: int = ALBUM_LIMIT) -> None:
    keepers = [frame for frame in frames if frame.status == "kept"]
    buckets: dict[str, list[Frame]] = {name: [] for name in SECTIONS}
    for frame in keepers:
        frame.section = _section_for(frame.face_count)
        buckets[frame.section].append(frame)
    for bucket in buckets.values():
        bucket.sort(key=lambda frame: frame.score, reverse=True)

    chosen: list[Frame] = []
    chosen_names: set[str] = set()
    scene_counts: dict[str, int] = {}

    def take(section: str, count: int, scene_cap: int) -> None:
        got = 0
        for frame in buckets[section]:
            if got >= count or len(chosen) >= limit:
                break
            if frame.filename in chosen_names:
                continue
            if scene_counts.get(frame.scene, 0) >= scene_cap:
                continue
            chosen.append(frame)
            chosen_names.add(frame.filename)
            scene_counts[frame.scene] = scene_counts.get(frame.scene, 0) + 1
            got += 1

    for section, count in SECTION_TARGETS.items():
        take(section, count, 2)
    if len(chosen) < limit:
        rest = sorted(keepers, key=lambda frame: frame.score, reverse=True)
        for frame in rest:
            if len(chosen) >= limit:
                break
            if frame.filename in chosen_names:
                continue
            if scene_counts.get(frame.scene, 0) >= 3:
                continue
            frame.section = frame.section or _section_for(frame.face_count)
            chosen.append(frame)
            chosen_names.add(frame.filename)
            scene_counts[frame.scene] = scene_counts.get(frame.scene, 0) + 1

    order = 0
    for section in SECTIONS:
        group = [frame for frame in chosen if frame.section == section]
        group.sort(key=lambda frame: frame.score, reverse=True)
        for frame in group:
            frame.status = "album"
            frame.album_order = order
            order += 1


def cluster_people(frames: list[Frame], use_sface: bool) -> list[dict]:
    pool = []
    for frame in frames:
        if frame.status not in {"kept", "album"}:
            continue
        for face in frame.faces:
            pool.append({"filename": frame.filename, "box": face["box"], "embedding": face["embedding"]})
    if not pool:
        return []
    matrix = np.stack([item["embedding"] for item in pool])
    similarity = matrix @ matrix.T
    threshold = FACE_MATCH if use_sface else HIST_MATCH
    parent = list(range(len(pool)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    for i in range(len(pool)):
        hits = np.where(similarity[i, i + 1 :] >= threshold)[0]
        for offset in hits:
            union(i, i + 1 + int(offset))

    groups: dict[int, list[int]] = {}
    for index in range(len(pool)):
        groups.setdefault(find(index), []).append(index)

    people = []
    for indexes in groups.values():
        names = {pool[i]["filename"] for i in indexes}
        if len(names) < 2:
            continue
        people.append({"members": [pool[i] for i in indexes], "filenames": names})
    people.sort(key=lambda person: len(person["filenames"]), reverse=True)
    return people


def validation(frames: list[Frame]) -> dict | None:
    labeled = [frame for frame in frames if frame.role in {"good", "dup", "bad"}]
    if not labeled:
        return None

    roots = {frame.duplicate_of for frame in labeled if frame.duplicate_of}

    def ratio(predicate_num, predicate_den) -> float | None:
        den = sum(1 for frame in labeled if predicate_den(frame))
        if not den:
            return None
        num = sum(1 for frame in labeled if predicate_den(frame) and predicate_num(frame))
        return round(num / den, 3)

    return {
        "good_kept": ratio(
            lambda frame: frame.status != "rejected",
            lambda frame: frame.role == "good",
        ),
        "duplicates_caught": ratio(
            lambda frame: frame.status == "duplicate" or frame.filename in roots,
            lambda frame: frame.role == "dup" and frame.status != "rejected",
        ),
        "rejects_caught": ratio(
            lambda frame: frame.status == "rejected",
            lambda frame: frame.role == "bad",
        ),
    }


def summarize(frames: list[Frame], people_count: int) -> dict:
    counts = {"rejected": 0, "duplicate": 0, "kept": 0, "album": 0}
    reasons: dict[str, int] = {}
    sections: dict[str, int] = {name: 0 for name in SECTIONS}
    for frame in frames:
        counts[frame.status] = counts.get(frame.status, 0) + 1
        if frame.reason and frame.status in {"rejected", "duplicate"}:
            reasons[frame.reason] = reasons.get(frame.reason, 0) + 1
        if frame.status == "album" and frame.section:
            sections[frame.section] = sections.get(frame.section, 0) + 1
    unique = counts["kept"] + counts["album"]
    return {
        "photo_count": len(frames),
        "rejected": counts["rejected"],
        "duplicates": counts["duplicate"],
        "unique_kept": unique,
        "album_count": counts["album"],
        "people_count": people_count,
        "reasons": reasons,
        "sections": sections,
    }
