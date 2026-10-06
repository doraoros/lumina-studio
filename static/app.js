const PHASES = [
  "Source photos",
  "3,000-frame shoot",
  "Quality",
  "Duplicates",
  "People",
  "Album",
];

const fmt = new Intl.NumberFormat("en-US");
const fmt1 = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const runButton = document.querySelector("#run");
const folderInput = document.querySelector("#folder");
const note = document.querySelector("#note");
const progress = document.querySelector("#progress");
const results = document.querySelector("#results");

function num(value) {
  return fmt.format(value || 0);
}
function hours(value) {
  return `${fmt1.format(value || 0)} h`;
}
function money(value) {
  return `${fmt.format(Math.round(value || 0))} RON`;
}
function pct(value) {
  if (value === null || value === undefined) return "—";
  return `${fmt1.format(value * 100)}%`;
}

function setProgress(job) {
  progress.hidden = false;
  document.querySelector("#phase").textContent = job.phase || "Preparing";
  document.querySelector("#percent").textContent = `${Math.round((job.progress || 0) * 100)}%`;
  document.querySelector("#bar").style.width = `${Math.round((job.progress || 0) * 100)}%`;
  document.querySelector("#detail").textContent = job.detail || "";
  const current = PHASES.indexOf(job.phase);
  document.querySelector("#phases").innerHTML = PHASES.map((name, index) => {
    const cls = index <= current ? "on" : "";
    return `<li class="${cls}">${name}</li>`;
  }).join("");
}

async function poll(jobId) {
  for (;;) {
    const response = await fetch(`/api/jobs/${jobId}`);
    const job = await response.json();
    setProgress(job);
    if (job.status === "done") return job.event_id;
    if (job.status === "error") throw new Error(job.error || "The analysis failed");
    await new Promise((resolve) => setTimeout(resolve, 700));
  }
}

function figure(photoId, caption) {
  return `<figure data-photo="${photoId}">
    <img src="/api/photos/${photoId}/image" alt="${caption}" loading="lazy" />
    <figcaption>${caption}</figcaption>
  </figure>`;
}

function countUp(el) {
  const target = Number(el.dataset.count);
  const kind = el.dataset.kind || "int";
  const start = performance.now();
  function frame(now) {
    const t = Math.min(1, (now - start) / 900);
    const value = target * (1 - (1 - t) ** 3);
    el.textContent = kind === "hours" ? hours(value) : num(Math.round(value));
    if (t < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function isCouple() {
  return document.body.classList.contains("role-couple");
}

function photoCaption(photo) {
  if (!photo) return "Photograph";
  if (isCouple()) return photo.section || "Photograph";
  return `score ${fmt1.format(photo.score)} · ${photo.face_count} faces`;
}

function albumMarkup(photos, perSection) {
  const loved = new Set(readStars());
  const sections = {};
  for (const photo of photos) {
    const name = photo.section || "Album";
    sections[name] = sections[name] || [];
    sections[name].push(photo);
  }
  return Object.entries(sections).map(([name, group]) => {
    group.sort((a, b) => Number(loved.has(b.id)) - Number(loved.has(a.id)));
    const shown = perSection ? group.slice(0, perSection) : group;
    return `
      <div class="album-section">
        <h3>${name}</h3>
        <div class="grid">
          ${shown.map((photo) => figure(photo.id, photoCaption(photo))).join("")}
        </div>
      </div>
    `;
  }).join("");
}

function chosenAlbum() {
  const album = results._album || [];
  const cut = isCouple() ? 0 : Number(results.querySelector("#cut")?.value || 0);
  if (!album.length || cut === 0) return album;
  const scores = album.map((photo) => photo.score);
  const low = Math.min(...scores);
  const high = Math.max(...scores);
  const threshold = low + ((high - low) * cut) / 100;
  return album.filter((photo) => photo.score >= threshold - 0.0001);
}

function paintAlbum() {
  const body = results.querySelector("#album-body");
  const readout = results.querySelector("#cut-readout");
  if (!body) return;
  const cut = Number(results.querySelector("#cut")?.value || 0);
  const photos = chosenAlbum();
  body.innerHTML = albumMarkup(photos, cut === 0 ? 8 : 12);
  if (readout) {
    readout.textContent = cut === 0
      ? `${num(photos.length)} frames in the album`
      : `${num(photos.length)} frames above the cut`;
  }
}

function readStars() {
  try {
    return JSON.parse(localStorage.getItem("lumina-shortlist") || "[]").map(Number);
  } catch {
    return [];
  }
}

function writeStars(ids) {
  localStorage.setItem("lumina-shortlist", JSON.stringify(ids));
}

function lovedPhotos() {
  const byId = results._byId || {};
  return readStars().map((id) => byId[id]).filter(Boolean);
}

function paintHandoff() {
  const box = results.querySelector("#handoff");
  if (!box) return;
  const loved = lovedPhotos();
  box.hidden = false;
  box.classList.toggle("ready", loved.length > 0);
  if (!loved.length) {
    box.innerHTML = "<p>The couple has not chosen yet. Switch to Couple and heart a few frames.</p>";
    return;
  }
  const noun = loved.length === 1 ? "photograph" : "photographs";
  box.innerHTML = `<p>The couple kept <strong>${num(loved.length)}</strong> ${noun}.</p><span>Open them first</span>`;
}

function paintShortlist() {
  const box = results.querySelector("#shortlist");
  const grid = results.querySelector("#shortlist-grid");
  if (!box || !grid) return;
  const ids = readStars();
  box.hidden = ids.length === 0;
  grid.innerHTML = ids.map((id) => {
    const photo = (results._byId || {})[id];
    const caption = photo ? photoCaption(photo) : (isCouple() ? "Favorite" : "Shortlist");
    return figure(id, caption);
  }).join("");
  paintHandoff();
}

function openFavorites() {
  const loved = lovedPhotos();
  if (!loved.length) return;
  clearInterval(reelTimer);
  reelTimer = null;
  viewList = loved;
  viewIndex = 0;
  showView();
}

function fanMarkup(group) {
  if (!group) return "";
  const ids = [group.keep_id, ...(group.dup_ids || [])].slice(0, 4);
  return `
    <button class="fan" id="fan" type="button">
      ${ids.map((id, index) => `<img style="--i:${index}" src="/api/photos/${id}/image" alt="">`).join("")}
      <span>Open the burst · ${num(group.copies)} copies removed</span>
    </button>
  `;
}

function render(data) {
  const summary = data.summary;
  const economics = summary.economics || {};
  const manual = economics.manual_hours || 1;
  const lumina = economics.lumina_hours || 0;
  const width = Math.max(8, Math.round((lumina / manual) * 100));

  const peopleHtml = data.people.length
    ? data.people.map((person) => `
        <article data-person="${person.id}" role="button" tabindex="0">
          ${person.cover_url ? `<img src="${person.cover_url}" alt="${person.label}" />` : ""}
          <strong>${person.label}</strong>
          <span>${num(person.photo_count)} frames</span>
        </article>
      `).join("")
    : "<p>No repeated identities were found in the selection.</p>";

  const compare = data.samples.compare;
  const wipeHtml = compare ? `
    <div class="wipe" id="wipe">
      <img class="wipe-base" src="/api/photos/${compare.after_id}/image" alt="Kept frame" />
      <div class="wipe-top">
        <img src="/api/photos/${compare.before_id}/image" alt="Soft frame" />
      </div>
      <input id="wipe-range" type="range" min="0" max="100" value="42" aria-label="Compare a soft frame with the kept frame" />
    </div>
    <p>Drag across the frame. Left is the soft shot Lumina rejected. Right is the one that stayed.</p>
  ` : "";
  const rejectedHtml = data.samples.rejected.map((photo) =>
    figure(photo.id, photo.reason || "Rejected")
  ).join("");

  const fan = fanMarkup(data.samples.duplicates[0]);
  const dupHtml = data.samples.duplicates.slice(1).map((group) => `
    <div class="pair">
      ${figure(group.keep_id, "Kept")}
      ${figure(group.dup_ids[0], `${num(group.copies)} copies removed`)}
    </div>
  `).join("");

  const validation = summary.validation;
  const validationHtml = validation ? `
    <div class="valid">
      <article><span>Good frames kept</span><strong>${pct(validation.good_kept)}</strong></article>
      <article><span>Duplicates caught</span><strong>${pct(validation.duplicates_caught)}</strong></article>
      <article><span>Weak frames rejected</span><strong>${pct(validation.rejects_caught)}</strong></article>
    </div>
  ` : "";

  const assumptions = (economics.assumptions || []).map((item) =>
    `<tr><td>${item.label}</td><td>${item.value}</td></tr>`
  ).join("");

  const preview = data.registry.preview.map((row) => `
    <tr>
      <td>${row.id}</td>
      <td>${row.filename}</td>
      <td>${row.status}</td>
      <td>${row.reason || "—"}</td>
      <td>${row.score}</td>
      <td>${row.face_count}</td>
    </tr>
  `).join("");

  const counts = data.registry.tables.map((table) =>
    `<b>${table.name} · ${num(table.rows)}</b>`
  ).join("");

  results.innerHTML = `
    <section class="results">
      <button id="handoff" class="handoff studio-only" type="button" hidden></button>
      <div class="studio-only">
        <p class="eyebrow">${data.event.name}</p>
        <h2>The selection is ready.</h2>
        <p class="quiet">${summary.source_note || ""} The run took ${num(Math.round(data.event.process_seconds))} seconds.</p>
      </div>
      <div class="couple-only">
        <p class="eyebrow">${data.event.name}</p>
        <h2>Your album is ready.</h2>
        <p class="quiet">Heart the photographs you want to keep. The studio will see your favorites.</p>
      </div>
      <div class="kpis studio-only">
        <article class="kpi"><span>Frames read</span><strong data-count="${summary.photo_count}">0</strong></article>
        <article class="kpi"><span>Duplicates removed</span><strong data-count="${summary.duplicates}">0</strong></article>
        <article class="kpi"><span>Final album</span><strong data-count="${summary.album_count}">0</strong></article>
        <article class="kpi"><span>Hours saved</span><strong data-count="${economics.saved_hours || 0}" data-kind="hours">0</strong></article>
      </div>
      <div class="funnel studio-only">
        <div><b>${num(summary.photo_count)}</b><span>uploaded</span></div>
        <div><b>${num(summary.rejected)}</b><span>rejected</span></div>
        <div><b>${num(summary.duplicates)}</b><span>duplicates</span></div>
        <div><b>${num(summary.unique_kept)}</b><span>unique keeps</span></div>
        <div><b>${num(summary.album_count)}</b><span>in the album</span></div>
      </div>

      <div class="compare studio-only">
        <div class="sheet">
          <h2>What left the album</h2>
          ${wipeHtml}
          ${fan}
          <p>Soft or badly exposed frames, next to bursts that keep a single variant.</p>
          <div class="rejects">${rejectedHtml}</div>
          ${dupHtml}
        </div>
        <div class="panel">
          <div class="econ-head"><h2>Studio impact</h2></div>
          <div class="bars">
            <div class="bar-row alt"><span><em>Manual culling</em><em>${hours(economics.manual_hours)}</em></span><i style="width:100%"></i></div>
            <div class="bar-row"><span><em>Lumina + review</em><em>${hours(economics.lumina_hours)}</em></span><i style="width:${width}%"></i></div>
          </div>
          <p class="callout">
            At ${economics.assumptions?.[3]?.value || "150 RON / hour"}, one event recovers
            <strong>${money(economics.labor_saved_ron)}</strong>.
            Across 6 events a month, that is <strong>${hours(economics.month_hours)}</strong>
            and <strong>${money(economics.month_labor_ron)}</strong> of culling time.
          </p>
          <p class="quiet">
            The freed culling capacity covers another ${fmt1.format(economics.selection_capacity || 0)} events,
            if the shoot day is not the constraint. The model uses an average package of ${money(economics.package_ron)}.
          </p>
          <table class="assumptions">${assumptions}</table>
          ${validationHtml}
        </div>
      </div>

      <div class="sheet">
        <div class="block-head">
          <div class="block-title">
            <h2 class="studio-only">Proposed album</h2>
            <h2 class="couple-only">The day</h2>
            <button id="play" class="play" type="button">Play album</button>
            <button id="open-book" class="play" type="button">Open the book</button>
          </div>
          <p class="studio-only">${num(summary.album_count)} frames · ${num(summary.people_count)} identities in the selection</p>
          <p class="couple-only">${num(summary.album_count)} photographs</p>
        </div>
        <div class="album-tools studio-only">
          <label>Cut line <input id="cut" type="range" min="0" max="100" value="0" aria-label="Album score cut"></label>
          <span id="cut-readout"></span>
        </div>
        <div id="shortlist" class="album-section" hidden>
          <h3 id="shortlist-title">${isCouple() ? "Favorites" : "Shortlist from the couple"}</h3>
          <div id="shortlist-grid" class="grid"></div>
        </div>
        <div id="album-body"></div>
        <div class="album-section">
          <h3 class="studio-only">People${data.people.length < summary.people_count ? ` · first ${data.people.length} of ${num(summary.people_count)}` : ""}</h3>
          <h3 class="couple-only">Find yourselves</h3>
          <div class="people">${peopleHtml}</div>
          <div id="person-strip" class="person-strip" hidden></div>
        </div>
      </div>

      <div class="panel registry studio-only">
        <h2>Event register</h2>
        <div class="tags">${counts}</div>
        <table class="data">
          <thead>
            <tr><th>ID</th><th>File</th><th>Status</th><th>Reason</th><th>Score</th><th>Faces</th></tr>
          </thead>
          <tbody>${preview}</tbody>
        </table>
      </div>
    </section>
  `;
  results._album = data.album;
  results._byId = Object.fromEntries(data.album.map((photo) => [photo.id, photo]));
  paintAlbum();
  paintShortlist();
  results.querySelector("#cut")?.addEventListener("input", paintAlbum);
  results.querySelectorAll("[data-count]").forEach(countUp);
  const wipe = results.querySelector("#wipe");
  const range = results.querySelector("#wipe-range");
  if (wipe && range) {
    const top = wipe.querySelector(".wipe-top");
    const overlay = top.querySelector("img");
    const sync = () => {
      overlay.style.width = `${wipe.clientWidth}px`;
      top.style.width = `${range.value}%`;
    };
    range.addEventListener("input", sync);
    requestAnimationFrame(sync);
  }
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

const stage = document.querySelector("#stage");
const stageImg = document.querySelector("#stage-img");
const stageCap = document.querySelector("#stage-cap");
const stageMeters = document.querySelector("#stage-meters");
const stageStar = document.querySelector("#stage-star");
const book = document.querySelector("#book");
let reelTimer = null;
let viewList = [];
let viewIndex = 0;
let bookIndex = 0;

function stopShow() {
  clearInterval(reelTimer);
  reelTimer = null;
  stage.hidden = true;
  stageImg.removeAttribute("src");
}

function paintMeters(photo) {
  if (!photo || (photo.sharpness == null && photo.score == null)) {
    stageMeters.hidden = true;
    return;
  }
  stageMeters.hidden = false;
  const rows = photo.sharpness == null
    ? [
        ["Score", photo.score, fmt1.format(photo.score)],
        ["Faces", Math.min((photo.face_count || 0) / 3, 1), String(photo.face_count || 0)],
      ]
    : [
        ["Sharpness", photo.sharpness, fmt1.format(photo.sharpness)],
        ["Exposure", photo.exposure, fmt1.format(photo.exposure)],
        ["Faces", Math.min((photo.face_count || 0) / 3, 1), String(photo.face_count || 0)],
      ];
  stageMeters.innerHTML = rows.map(([label, value, text]) => `
    <div><span>${label}</span><i style="width:${Math.round(Math.max(0, Math.min(1, value)) * 100)}%"></i><b>${text}</b></div>
  `).join("");
}

function paintStar(photoId) {
  const on = readStars().includes(Number(photoId));
  if (isCouple()) stageStar.textContent = on ? "Loved" : "Love this";
  else stageStar.textContent = on ? "On the shortlist" : "Add to shortlist";
  stageStar.classList.toggle("on", on);
  stageStar.dataset.id = String(photoId);
}

function showView() {
  const photo = viewList[viewIndex];
  if (!photo) return;
  stage.hidden = false;
  stageImg.src = `/api/photos/${photo.id}/image`;
  stageCap.textContent = photo.section || photo.caption || "Frame";
  paintMeters(photo.sharpness == null ? (results._byId || {})[photo.id] : photo);
  paintStar(photo.id);
}

function openStill(photoId, caption) {
  clearInterval(reelTimer);
  reelTimer = null;
  const known = (results._byId || {})[Number(photoId)];
  const album = results._album || [];
  const index = album.findIndex((photo) => photo.id === Number(photoId));
  if (index >= 0) {
    viewList = album;
    viewIndex = index;
  } else {
    viewList = [{ id: Number(photoId), caption, ...(known || {}) }];
    viewIndex = 0;
  }
  showView();
}

function playAlbum(album) {
  const buckets = {};
  for (const photo of album) {
    buckets[photo.section] = buckets[photo.section] || [];
    buckets[photo.section].push(photo);
  }
  const reel = [];
  for (let index = 0; index < 5; index += 1) {
    for (const group of Object.values(buckets)) {
      if (group[index]) reel.push(group[index]);
    }
  }
  if (!reel.length) return;
  viewList = reel;
  viewIndex = 0;
  showView();
  clearInterval(reelTimer);
  reelTimer = setInterval(() => {
    viewIndex = (viewIndex + 1) % viewList.length;
    showView();
  }, 2400);
}

function withLovedFirst(list) {
  const rank = new Map(readStars().map((id, index) => [id, index]));
  return [...list].sort((a, b) => (rank.get(a.id) ?? 10000) - (rank.get(b.id) ?? 10000));
}

function paintBook() {
  const album = withLovedFirst(chosenAlbum());
  if (album.length < 2) return;
  if (bookIndex >= album.length) bookIndex = 0;
  if (bookIndex < 0) bookIndex = Math.max(0, album.length - (album.length % 2 === 0 ? 2 : 1));
  const left = album[bookIndex];
  const right = album[bookIndex + 1] || album[0];
  const leftImg = document.querySelector("#page-left");
  const rightImg = document.querySelector("#page-right");
  leftImg.src = `/api/photos/${left.id}/image`;
  rightImg.src = `/api/photos/${right.id}/image`;
  document.querySelector("#page-left-cap").textContent = left.section || "";
  document.querySelector("#page-right-cap").textContent = right.section || "";
  const page = Math.floor(bookIndex / 2) + 1;
  const pages = Math.ceil(album.length / 2);
  document.querySelector("#book-cap").textContent = `Spread ${page} of ${pages}`;
}

function openBook() {
  bookIndex = 0;
  book.hidden = false;
  paintBook();
}

document.querySelector("#stage-close").addEventListener("click", stopShow);
stageStar.addEventListener("click", () => {
  const id = Number(stageStar.dataset.id);
  if (!id) return;
  const ids = readStars();
  const next = ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id];
  writeStars(next);
  paintStar(id);
  paintShortlist();
});
document.querySelector("#book-close").addEventListener("click", () => {
  book.hidden = true;
});
document.querySelector("#book-next").addEventListener("click", () => {
  bookIndex += 2;
  paintBook();
});
document.querySelector("#book-prev").addEventListener("click", () => {
  bookIndex = Math.max(0, bookIndex - 2);
  paintBook();
});
stage.addEventListener("click", (event) => {
  if (event.target === stage) stopShow();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (!book.hidden) {
      book.hidden = true;
      return;
    }
    if (!document.querySelector("#gate").hidden) {
      closeGate();
      return;
    }
    stopShow();
    return;
  }
  if (!book.hidden && (event.key === "ArrowRight" || event.key === "ArrowLeft")) {
    bookIndex += event.key === "ArrowRight" ? 2 : -2;
    if (bookIndex < 0) bookIndex = 0;
    paintBook();
    return;
  }
  if (stage.hidden || !viewList.length) return;
  if (event.key === "ArrowRight") {
    clearInterval(reelTimer);
    reelTimer = null;
    viewIndex = (viewIndex + 1) % viewList.length;
    showView();
  }
  if (event.key === "ArrowLeft") {
    clearInterval(reelTimer);
    reelTimer = null;
    viewIndex = (viewIndex - 1 + viewList.length) % viewList.length;
    showView();
  }
});

results.addEventListener("click", async (event) => {
  const fanButton = event.target.closest("#fan");
  if (fanButton) {
    fanButton.classList.toggle("open");
    return;
  }
  if (event.target.closest("#open-book")) {
    openBook();
    return;
  }
  if (event.target.closest("#handoff")) {
    if (lovedPhotos().length) openFavorites();
    else setRole("couple");
    return;
  }
  if (event.target.closest("#play")) {
    const payload = results._album || [];
    playAlbum(payload);
    return;
  }
  const shot = event.target.closest("figure[data-photo]");
  if (shot && !event.target.closest("#wipe")) {
    openStill(shot.dataset.photo, shot.querySelector("figcaption")?.textContent || "");
    return;
  }
  const person = event.target.closest("[data-person]");
  if (!person) return;
  results.querySelectorAll("[data-person]").forEach((item) => item.classList.remove("active"));
  person.classList.add("active");
  const strip = results.querySelector("#person-strip");
  strip.hidden = false;
  strip.innerHTML = "<p>Loading frames…</p>";
  const response = await fetch(`/api/people/${person.dataset.person}/photos`);
  if (!response.ok) {
    strip.innerHTML = "<p>No frames for this person.</p>";
    return;
  }
  const payload = await response.json();
  strip.innerHTML = (payload.photos || []).map((photo) => figure(photo.id, photo.section || "Frame")).join("");
});

function studioOpen() {
  return sessionStorage.getItem("lumina-studio-open") === "1";
}

function openGate() {
  const gate = document.querySelector("#gate");
  gate.hidden = false;
  document.querySelector("#gate-error").hidden = true;
  document.querySelector("#gate-code").value = "";
  document.querySelector("#gate-code").focus();
}

function closeGate() {
  document.querySelector("#gate").hidden = true;
}

function setRole(role) {
  if (role === "studio" && !studioOpen()) {
    openGate();
    return;
  }
  const couple = role !== "studio";
  document.body.classList.toggle("role-couple", couple);
  document.body.classList.toggle("role-studio", !couple);
  localStorage.setItem("lumina-role", couple ? "couple" : "studio");
  document.querySelectorAll(".role [data-role]").forEach((button) => {
    button.classList.toggle("on", button.dataset.role === (couple ? "couple" : "studio"));
  });
  const meta = document.querySelector(".nav-meta");
  if (meta) meta.textContent = couple ? "Your wedding album" : "Selection and albums for photo studios";
  const title = document.querySelector("#shortlist-title");
  if (title) title.textContent = couple ? "Favorites" : "Shortlist from the couple";
  if (results._album) {
    paintAlbum();
    paintShortlist();
  }
  if (!stage.hidden && stageStar.dataset.id) paintStar(stageStar.dataset.id);
}

document.querySelector(".role").addEventListener("click", (event) => {
  const button = event.target.closest("[data-role]");
  if (button) setRole(button.dataset.role);
});

document.querySelector("#gate-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const code = document.querySelector("#gate-code").value.trim().toLowerCase();
  if (code !== "lumina") {
    document.querySelector("#gate-error").hidden = false;
    return;
  }
  sessionStorage.setItem("lumina-studio-open", "1");
  closeGate();
  setRole("studio");
});
document.querySelector("#gate-cancel").addEventListener("click", closeGate);

async function loadExisting() {
  const response = await fetch("/api/demo");
  const payload = await response.json();
  const coupleNote = document.querySelector("#couple-note");
  if (!payload.event) {
    note.textContent = "The demo builds 3,000 frames from real photographs, then culls them in front of you.";
    if (coupleNote) coupleNote.textContent = "The album is still being prepared.";
    return;
  }
  note.textContent = "An event is already processed. Review the album, or run it again.";
  if (coupleNote) coupleNote.textContent = "";
  runButton.textContent = "Run again";
  render(payload.event);
}

runButton.addEventListener("click", async () => {
  runButton.disabled = true;
  results.innerHTML = "";
  try {
    const response = await fetch("/api/demo/run", { method: "POST" });
    if (!response.ok) throw new Error(await response.text());
    const { job_id: jobId } = await response.json();
    const eventId = await poll(jobId);
    const detail = await fetch(`/api/events/${eventId}`);
    render(await detail.json());
    progress.hidden = true;
    runButton.textContent = "Run again";
  } catch (error) {
    note.textContent = error.message;
  } finally {
    runButton.disabled = false;
  }
});

folderInput.addEventListener("change", async () => {
  const files = [...folderInput.files].filter((file) => /\.(jpe?g|png|webp)$/i.test(file.name));
  if (!files.length) return;
  runButton.disabled = true;
  results.innerHTML = "";
  progress.hidden = false;
  try {
    const opened = await fetch("/api/uploads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Own folder" }),
    });
    const { event_id: eventId } = await opened.json();
    const batchSize = 12;
    for (let index = 0; index < files.length; index += batchSize) {
      const batch = files.slice(index, index + batchSize);
      const body = new FormData();
      batch.forEach((file) => body.append("files", file, file.name));
      await fetch(`/api/events/${eventId}/files`, { method: "POST", body });
      setProgress({
        phase: "Source photos",
        progress: (index + batch.length) / files.length * 0.35,
        detail: `${Math.min(index + batch.length, files.length)} / ${files.length} files received`,
      });
    }
    const started = await fetch(`/api/events/${eventId}/process`, { method: "POST" });
    const { job_id: jobId } = await started.json();
    const doneId = await poll(jobId);
    const detail = await fetch(`/api/events/${doneId}`);
    render(await detail.json());
    progress.hidden = true;
  } catch (error) {
    note.textContent = error.message;
  } finally {
    runButton.disabled = false;
    folderInput.value = "";
  }
});

setRole(studioOpen() && localStorage.getItem("lumina-role") !== "couple" ? "studio" : "couple");
loadExisting();
