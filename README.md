# lumina-studio

Lumina culls a wedding shoot for a photo studio. It reads each frame, rejects the ones that are soft or badly exposed, collapses near-duplicate bursts, groups people, and proposes an album of 160 photographs. The same wedding then opens as two views: the studio desk, and the album the couple actually looks at.

Decisions come from the pixels. Nothing in the culling step reads a filename or a hand-written label.

## The two views

The page opens on **Couple**. That view is the album, a slideshow, a book, the people found in the day, and a heart on the frames they want to keep. It does not show scores, the reject pile, the registry, or the money.

**Studio** is the desk: the funnel, the cut line, duplicate and reject inspection, the hours and RON, and the shortlist the couple sent back. It asks for a code. The demo code is `lumina`. You type it once per browser tab; a new tab asks again. After it is open, Studio can still switch to Couple and see the same wedding.

Hearts live in the browser (`localStorage`). When the couple has chosen, Studio shows how many frames they kept and can open those first. The book starts with them too.

## The demo wedding

“Run the demo wedding” does not download 3,000 unrelated photographs. It starts from **56 real wedding photographs** (Wikimedia Commons and Unsplash), kept only when they are sharp, well exposed, and contain a face at least 48 pixels wide. Each source becomes one scene, and the scene is expanded until the shoot has **3,000 frames**:

- a few good crops of that photograph
- near-duplicate bursts (light noise, JPEG quality 78)
- failed frames: strong blur, underexposure, blown highlights

The labels `good`, `dup`, and `bad` exist only so the demo can check itself afterwards. The pipeline never reads them. A duplicate that scores higher than its pair is kept on purpose: the studio wants the better file, not the file that happened to be tagged “original”.

The first full run downloads the face models, fetches the source photographs, and writes `data/`. Later visits reload the event already stored in SQLite.

You can also upload your own folder. Those frames have no demo labels, so there is no validation score — only the same pixel decisions.

## How a frame is decided

1. **Read.** An unreadable file is rejected as `Unreadable`.
2. **Sharpness.** Variance of a Laplacian, mapped with `v / (v + 90)`. Below **0.38** the frame is `Soft`.
3. **Exposure.** Distance of the mean gray from a usable mid-tone band, reduced when many pixels are clipped. Below **0.50** the frame is `Poor exposure`.
4. **Score.** `0.72 * sharpness + 0.28 * exposure`. If a face pass runs and the frame is still kept, a small bonus is added for one or two faces.
5. **Duplicates.** A 64-bit difference hash. Inside one scene, frames within Hamming distance **5** are one burst. The highest score stays; the rest are `Duplicate`.
6. **Faces.** YuNet finds faces. SFace embeddings are clustered by cosine similarity (threshold **0.45**). If SFace is unavailable, a color histogram is used instead (threshold **0.93**). A person needs at least two photographs.
7. **Album.** Keepers are split by face count: two faces → Couple, one → Portraits, three or more → Guests, none → Details. The album holds at most **160** frames, a few per scene, highest score first.

OpenCV **4.11** is pinned. YuNet on OpenCV 5 barely detected faces on these photographs.

## Time and money

The hours and RON on the studio desk are a worked example, not a survey of studios. The assumptions, also shown in the interface:

| Assumption | Value |
| --- | --- |
| Manual decision per frame | 6.5 seconds |
| Grouping people and sequencing by hand | 70 minutes |
| Reviewing what Lumina proposed | 18 minutes |
| Post-production rate | 150 RON / hour |
| Events per month | 6 |
| Average wedding package | 6,500 RON |

Manual time is `frames × 6.5s + 70 min`. Lumina time is the measured processing run plus 18 minutes of review. The difference is multiplied by the hourly rate, then by six events.

## Run it

Python 3.12. From the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8741
```

Open [http://127.0.0.1:8741](http://127.0.0.1:8741). If `py` is not on your PATH, call the Python you installed, then use the `python.exe` inside `.venv` for the server.

HTML, CSS, and JavaScript are read from disk, so a refresh picks up interface changes. Changes under `app/` need a restart.

## What is stored

SQLite at `data/lumina.db` (WAL):

- `events` — one wedding, its runtime, and the summary JSON
- `photos` — path, scene, scores, status (`rejected`, `duplicate`, `kept`, `album`), reason, section
- `people` and `faces` — clusters and the boxes that produced them

`data/` is gitignored. It holds the source photographs, the 3,000 frames, the ONNX models, and the database. Deleting it means the next demo run builds the shoot again.

## Layout

```
app/config.py     paths and the 3,000 / 160 limits
app/dataset.py    source download and the generated shoot
app/pipeline.py   sharpness, exposure, duplicates, faces, album
app/economics.py  the hour and RON assumptions
app/db.py         SQLite schema
app/service.py    jobs, persistence, the event the page reads
app/main.py       HTTP API and the static page
static/           the studio and couple interface
```

## Limits worth saying out loud

- The 3,000 frames are derived from 56 photographs. They show that the pipeline can cull a full shoot. They are not 3,000 independent real photos.
- Validation on the demo set measures agreement with the generated labels. It does not measure agreement with a photographer.
- Person groups are embeddings of faces cropped from those same sources. They are useful in the demo and imperfect as identity.
- The economic figures move if you change the six assumptions in `app/economics.py`.
