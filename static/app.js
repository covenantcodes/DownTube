const $ = id => document.getElementById(id);

const QUALITY_LABELS = {
  best: "Best quality",
  "1080": "1080p",
  "720": "720p",
  "480": "480p",
  audio: "Audio only (MP3)",
};

const GENERIC_ERROR = "Something went wrong. That link might be private, restricted, or invalid.";

function escapeHtml(str) {
  return str.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function setStatus(msg, type = "") {
  const el = $("status");
  el.className = type;

  if (type === "err") {
    el.innerHTML = `${GENERIC_ERROR}<details class="status-details"><summary>Details</summary><code>${escapeHtml(msg)}</code></details>`;
  } else {
    el.textContent = msg;
  }
}

function formatDuration(seconds) {
  if (!seconds) return "";
  seconds = Math.round(seconds);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

async function api(path, body) {
  const res = await fetch(path, body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : {});
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

async function fetchVideoInfo() {
  const url = $("url").value.trim();
  if (!url) return;

  $("fetchBtn").disabled = true;
  $("preview").style.display = "none";
  $("bar").style.display = "none";
  setStatus("Fetching video info…");

  try {
    const info = await api("/api/info", { url });
    $("thumb").src = info.thumbnail || "";
    $("title").textContent = info.title;
    $("sub").innerHTML = [info.channel, formatDuration(info.duration)]
      .filter(Boolean)
      .map(value => `<span class="chip">${value}</span>`)
      .join("");
    $("quality").innerHTML = info.qualities
      .map(q => `<option value="${q}">${QUALITY_LABELS[q]}</option>`)
      .join("");
    $("preview").style.display = "block";
    setStatus("");
  } catch (e) {
    setStatus(e.message, "err");
  }

  $("fetchBtn").disabled = false;
}

async function startDownload() {
  $("dlBtn").disabled = true;
  $("bar").style.display = "block";
  $("fill").style.width = "0";
  setStatus("Starting…");

  const stop = (poll, msg, type) => {
    clearInterval(poll);
    setStatus(msg, type);
    $("dlBtn").disabled = false;
  };

  try {
    const { job_id } = await api("/api/download", {
      url: $("url").value.trim(),
      quality: $("quality").value,
    });

    const poll = setInterval(async () => {
      try {
        const p = await api(`/api/progress/${job_id}`);
        $("fill").style.width = p.progress + "%";

        if (p.status === "downloading") {
          setStatus(`Downloading ${p.progress}%${p.speed ? " · " + p.speed : ""}`);
        } else if (p.status === "processing") {
          setStatus("Merging / converting…");
        } else if (p.status === "done") {
          stop(poll, "Done — saving file.", "ok");
          window.location.href = `/api/file/${job_id}`;
        } else if (p.status === "error") {
          stop(poll, p.error, "err");
        }
      } catch (e) {
        stop(poll, e.message, "err");
      }
    }, 800);
  } catch (e) {
    setStatus(e.message, "err");
    $("dlBtn").disabled = false;
  }
}

const THEME_KEY = "downtube-theme";

function storedTheme() {
  try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
}

function prefersDark() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function isDark() {
  const stored = storedTheme();
  return stored ? stored === "dark" : prefersDark();
}

function syncThemeToggle() {
  const dark = isDark();
  $("themeToggle").textContent = dark ? "☀" : "☾";
  $("themeToggle").setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
}

function toggleTheme() {
  const next = isDark() ? "light" : "dark";
  try { localStorage.setItem(THEME_KEY, next); } catch (e) {}
  document.documentElement.setAttribute("data-theme", next);
  syncThemeToggle();
}

$("fetchBtn").onclick = fetchVideoInfo;
$("dlBtn").onclick = startDownload;
$("themeToggle").onclick = toggleTheme;
$("url").addEventListener("keydown", e => {
  if (e.key === "Enter") $("fetchBtn").click();
});

syncThemeToggle();
