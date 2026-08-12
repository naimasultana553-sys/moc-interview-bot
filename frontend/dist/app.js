"use strict";

/* ==================================================================
   AI Interview Bot — frontend controller (dark "AI lab" theme)
   ================================================================== */

const ROLES = [
  "Software Engineer", "Frontend Developer", "Backend Developer",
  "Full Stack Developer", "Machine Learning Engineer", "Data Scientist",
  "Mobile App Developer", "UI/UX Designer",
];

const DIM_KEYS = [
  "Relevance", "Technical Accuracy", "Completeness",
  "Communication", "Clarity", "Confidence", "Problem Solving",
];

const SAMPLE_RESUME = `Sarah Johnson
sarah.johnson@example.com
+1 555-123-4567
San Francisco, CA | github.com/sarahj | linkedin.com/in/sarahjohnson

SUMMARY
Software engineer with 4 years of experience building web applications. Strong background in Python, JavaScript, and React with a focus on machine learning productization.

EDUCATION
B.Sc. Computer Science, University of California, 2019
M.S. Data Science, Stanford University, 2021

SKILLS
Python, JavaScript, TypeScript, React, Node.js, Django, PostgreSQL, MongoDB, Redis, Docker, Kubernetes, AWS, Git

PROJECTS
AI Resume Parser - Built a document parsing pipeline with Python, Django, and PostgreSQL. Used NLP techniques and deployed with Docker on AWS.
Sentiment Analysis Dashboard - React and Flask application that visualizes sentiment trends using pandas and scikit-learn.

EXPERIENCE
Backend Engineer, TechCorp, 2022 - Present
- Designed and built REST APIs serving 50k daily active users
Software Engineer, DataWorks, 2019 - 2022
- Built ETL pipelines in Python processing 2M records daily

CERTIFICATIONS
AWS Certified Solutions Architect
Google Cloud Professional Data Engineer
`;

/* ----------------------------------------------------------------
   State
   ---------------------------------------------------------------- */
const state = {
  sessionId: null,
  resume: null,
  summary: "",
  next: null,           // current question payload
  report: null,
  session: null,
  aiMode: "offline",
  busy: false,
  history: [],          // {q, a, isFollow} rendered in interview room
  cats: {},             // category -> 'done'|'current'
  durationMs: 1200000,
  timerId: null,
  endTime: 0,
};

/* ----------------------------------------------------------------
   DOM helpers
   ---------------------------------------------------------------- */
const $ = (id) => document.getElementById(id);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function api(path, options) {
  return fetch(path, options).then((res) => {
    return res.json().catch(() => null).then((body) => {
      if (!res.ok) {
        const detail = (body && (body.detail || body.message)) || `Request failed (${res.status})`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      return body;
    });
  });
}

function showView(name) {
  document.querySelectorAll(".view").forEach((v) => (v.hidden = true));
  const el = $("view-" + name);
  if (el) el.hidden = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function escapeHtml(v) {
  return String(v == null ? "" : v).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function setError(text, el) {
  if (!el) return;
  el.hidden = !text;
  el.textContent = text || "";
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(t._t);
  t._t = setTimeout(() => (t.hidden = true), 3200);
}

function scoreClass(s) {
  if (s >= 7) return "good";
  if (s >= 5) return "ok";
  return "low";
}

/* ----------------------------------------------------------------
   Neural background canvas
   ---------------------------------------------------------------- */
function initNeural() {
  const c = $("neural-bg");
  if (!c) return;
  const ctx = c.getContext("2d");
  let w, h, pts, raf, running = true;

  function resize() {
    w = c.width = window.innerWidth;
    h = c.height = window.innerHeight;
    const n = Math.min(70, Math.floor((w * h) / 22000));
    pts = Array.from({ length: n }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35,
    }));
  }
  function tick() {
    if (!running) return;
    ctx.clearRect(0, 0, w, h);
    const max = 150;
    for (const p of pts) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;
    }
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
        const d = Math.hypot(dx, dy);
        if (d < max) {
          const a = (1 - d / max) * 0.25;
          ctx.strokeStyle = `rgba(80,170,255,${a})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(pts[i].x, pts[i].y);
          ctx.lineTo(pts[j].x, pts[j].y);
          ctx.stroke();
        }
      }
    }
    for (const p of pts) {
      ctx.fillStyle = "rgba(120,200,255,0.55)";
      ctx.beginPath();
      ctx.arc(p.x, p.y, 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
    raf = requestAnimationFrame(tick);
  }
  resize();
  window.addEventListener("resize", resize);
  document.addEventListener("visibilitychange", () => {
    running = !document.hidden;
    if (running) tick();
    else cancelAnimationFrame(raf);
  });
  tick();
}

/* ----------------------------------------------------------------
   Step + nav helpers
   ---------------------------------------------------------------- */
function setSteps(view) {
  const bars = view === "upload" ? [$("steps-bar")] : $$('[data-steps]');
  bars.forEach((bar) => {
    if (!bar) return;
    const order = ["upload", "analysis", "setup", "report"];
    const idx = order.indexOf(view);
    bar.querySelectorAll(".step").forEach((s, i) => {
      s.classList.toggle("active", i === idx);
    });
  });
}

function scrollToSection(id) {
  showView("landing");
  setTimeout(() => {
    const t = document.getElementById(id);
    if (t) t.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 60);
}

/* ================================================================
   LANDING
   ================================================================ */
function goToUpload() {
  if (!state.sessionId) {
    showView("upload");
    setSteps("upload");
    return;
  }
  // Resume already uploaded this session; jump to analysis.
  renderAnalysis();
  showView("analysis");
  setSteps("analysis");
}

/* ================================================================
   RESUME UPLOAD
   ================================================================ */
async function analyzeResume(file) {
  setError("", $("upload-error"));
  $("file-card-name").textContent = file.name || "resume.pdf";
  $("file-card-size").textContent = "Uploading…";
  $("dropzone").hidden = true;
  $("file-card").hidden = false;
  $("ai-processing").hidden = true;
  $("continue-btn").hidden = true;
  let p = 0;
  const prog = setInterval(() => {
    p = Math.min(100, p + 12 + Math.random() * 10);
    $("upload-fill").style.width = p + "%";
    if (p >= 100) clearInterval(prog);
  }, 120);

  await delay(750);
  clearInterval(prog);
  $("upload-fill").style.width = "100%";
  $("file-card-size").textContent = formatBytes(file.size);
  $("ai-processing").hidden = false;
  runStages(["Reading resume", "Extracting information", "Identifying skills", "Preparing interview context"], $("stage-list"));

  try {
    const fd = new FormData();
    fd.append("file", file, file.name || "resume.pdf");
    const data = await api("/api/resume/analyze", { method: "POST", body: fd });
    state.sessionId = data.session_id;
    state.resume = data.resume;
    state.summary = data.summary;
    localStorage.setItem("moc_session_id", state.sessionId);
    markStagesDone($("stage-list"));
    $("ai-stage-title").textContent = "Resume analyzed successfully ✓";
    $("continue-btn").hidden = false;
  } catch (err) {
    clearInterval(prog);
    $("ai-processing").hidden = true;
    $("file-card").hidden = true;
    $("dropzone").hidden = false;
    setError(err.message || "Could not read this file. Please upload a valid PDF or TXT.", $("upload-error"));
  }
}

function runStages(labels, list) {
  list.innerHTML = labels
    .map((l, i) => `<li class="${i === 0 ? "active" : ""}" data-stage><span>${escapeHtml(l)}</span></li>`)
    .join("");
}
function markStagesDone(list) {
  list.querySelectorAll("li").forEach((li, i) => {
    li.classList.remove("active");
    li.classList.add(i === list.children.length - 1 ? "active" : "done");
  });
}

function formatBytes(b) {
  if (!b && b !== 0) return "";
  if (b < 1024) return b + " B";
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + " KB";
  return (b / (1024 * 1024)).toFixed(1) + " MB";
}
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

/* ================================================================
   RESUME ANALYSIS (step 02)
   ================================================================ */
function renderAnalysis() {
  const r = state.resume || {};
  $("analysis-name").textContent = r.name || "Candidate";
  $("analysis-focus").textContent = (r.summary || "").slice(0, 120) || "Professional focus";
  $("analysis-candidate").textContent = r.name ? `${r.name} · ${r.skills ? r.skills.length : 0} skills parsed` : "";
  $("analysis-summary").textContent = state.summary || buildSummary(r);
  $("analysis-avatar").textContent = (r.name || "AI").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  renderChips("ic-skills", r.skills || []);
  renderList("ic-education", (r.education || []).map((e) => [e.degree, e.institution, e.year].filter(Boolean).join(", ")).filter(Boolean));
  renderList("ic-projects", (r.projects || []).map((p) => p.name).filter(Boolean));
  renderList("ic-experience", (r.experience || []).map((e) => [e.role, e.company].filter(Boolean).join(" — ")).filter(Boolean).slice(0, 4));
  renderList("ic-certifications", r.certifications || []);

  const insights = [];
  if ((r.skills || []).length) insights.push(`Strongest area: ${r.skills.slice(0, 3).join(", ")}.`);
  if ((r.projects || []).length) insights.push("Interview focus likely on your projects and hands-on experience.");
  if ((r.experience || []).length) insights.push(`Detected ${r.experience.length} role(s) of experience.`);
  $("analysis-insights").innerHTML = insights.map((i) => `<li>${escapeHtml(i)}</li>`).join("") || "<li>No insights available.</li>";
}

function renderChips(id, items) {
  $(id).innerHTML = (items || []).slice(0, 24).map((i) => `<span class="chip">${escapeHtml(i)}</span>`).join("") || `<span class="chip">—</span>`;
}
function renderList(id, items) {
  $(id).innerHTML = (items && items.length)
    ? items.map((i) => `<li>${escapeHtml(i)}</li>`).join("")
    : "<li>None detected.</li>";
}
function buildSummary(r) {
  const top = (r.technologies || []).slice(0, 5).join(", ") || "no explicit technologies listed";
  return `Candidate: ${r.name || "Unknown"} · ${(r.skills || []).length} skills detected · ${(r.experience || []).length} roles · ${(r.projects || []).length} projects. Highlights: ${top}.`;
}

/* ================================================================
   INTERVIEW SETUP (step 03)
   ================================================================ */
let selectedRole = "Software Engineer";

function buildSetup() {
  const grid = $("role-options");
  grid.innerHTML = ROLES.map(
    (role) => `<label class="opt"><input type="radio" name="role" value="${escapeHtml(role)}" ${role === selectedRole ? "checked" : ""}><span>${escapeHtml(role)}</span></label>`
  ).join("") +
    `<label class="opt"><input type="radio" name="role" value="__custom__"><span>Custom Role</span></label>`;

  grid.addEventListener("change", (e) => {
    const v = e.target.value;
    if (v === "__custom__") {
      $("custom-role").hidden = false;
      $("custom-role").focus();
    } else {
      $("custom-role").hidden = true;
      selectedRole = v;
    }
    updatePreview();
  });
  $("custom-role").addEventListener("input", updatePreview);

  $$("#difficulty-options input, #count-options input, #duration-options input").forEach((i) =>
    i.addEventListener("change", updatePreview)
  );
  updatePreview();
}

function getVal(name) {
  const el = document.querySelector(`input[name="${name}"]:checked`);
  return el ? el.value : null;
}

function updatePreview() {
  const role = $("custom-role").hidden ? selectedRole : ($("custom-role").value.trim() || "Custom Role");
  $("pv-role").textContent = role;
  $("pv-diff").textContent = capitalize(getVal("diff") || "medium");
  $("pv-type").textContent = "Mixed";
  $("pv-count").textContent = getVal("count") || "10";
  const dur = parseInt(getVal("duration") || "1200", 10);
  $("pv-time").textContent = Math.round(dur / 60) + " min";
}

function capitalize(s) { return (s || "").charAt(0).toUpperCase() + (s || "").slice(1); }

async function generateInterview() {
  const role = $("custom-role").hidden ? selectedRole : ($("custom-role").value.trim() || selectedRole);
  const difficulty = getVal("diff") || "medium";
  const num = parseInt(getVal("count") || "10", 10);
  state.durationMs = parseInt(getVal("duration") || "1200", 10) * 1000;

  setError("", $("setup-error"));
  $("generate-btn").disabled = true;
  try {
    showGenerating();
    const data = await api(`/api/interview/${state.sessionId}/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_role: role, difficulty, num_questions: num }),
    });
    state.next = data.next;
    state.history = [];
    state.cats = {};
    // small delay so the generating animation reads
    await delay(900);
    showInterview();
  } catch (err) {
    setError(err.message, $("setup-error"));
    showView("setup");
    setSteps("setup");
  } finally {
    $("generate-btn").disabled = false;
  }
}

/* ================================================================
   GENERATING SCREEN
   ================================================================ */
function showGenerating() {
  const stages = [
    { t: "Resume analyzed", s: "done" },
    { t: "Job role identified", s: "done" },
    { t: "Difficulty configured", s: "done" },
    { t: "Generating personalized questions", s: "active" },
    { t: "Preparing adaptive follow-ups", s: "pending" },
  ];
  $("gen-stages").innerHTML = stages
    .map((x) => `<li class="${x.s === "active" ? "active" : x.s === "done" ? "done" : ""}"><span>${x.t}</span></li>`)
    .join("");
  showView("generating");
}

/* ================================================================
   INTERVIEW ROOM
   ================================================================ */
function showInterview() {
  // reset interview container history
  renderProgressPanel();
  renderNextQuestion();
  showView("interview");
  startTimer(state.durationMs);
}

function startTimer(ms) {
  clearInterval(state.timerId);
  state.endTime = Date.now() + ms;
  const tick = () => {
    const rem = Math.max(0, state.endTime - Date.now());
    const m = Math.floor(rem / 60000);
    const s = Math.floor((rem % 60000) / 1000);
    const t = $("timer");
    t.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    t.classList.toggle("warning", rem <= 60000 && rem > 10000);
    t.classList.toggle("critical", rem <= 10000);
    if (rem <= 0) {
      clearInterval(state.timerId);
      openEndModal();
    }
  };
  tick();
  state.timerId = setInterval(tick, 1000);
}

function catFor(type) {
  if (type === "technical" || type === "cv") return "Technical";
  if (type === "behavioral") return "Behavioral";
  if (type === "project") return "Project";
  if (type === "situational") return "Situational";
  return "Technical";
}

function renderProgressPanel() {
  const total = state.next ? state.next.total : 0;
  const answered = state.history.length;
  $("pp-count").textContent = `${answered} / ${total}`;
  $("pp-bar").style.width = (total ? Math.min(100, (answered / total) * 100) : 0) + "%";
  $("pp-role").textContent = ($("pv-role").textContent || "—");
  $("pp-diff").textContent = capitalize(getVal("diff") || "medium");
  $("pp-type").textContent = "Mixed";
  $$("#pp-cats li").forEach((li) => {
    const cat = li.dataset.cat;
    li.classList.toggle("done", state.cats[cat] === "done");
    li.classList.toggle("current", state.cats[cat] === "current");
  });
}

function renderNextQuestion() {
  const nxt = state.next;
  const qp = $("question-panel");
  const ap = $("answer-panel");
  if (!nxt || !nxt.question) {
    qp.hidden = true;
    ap.hidden = true;
    renderFinishBanner();
    return;
  }
  qp.hidden = false;
  ap.hidden = false;
  const q = nxt.question;
  $("q-label").textContent = `QUESTION ${String(nxt.question_number).padStart(2, "0")}`;
  $("q-meta").textContent = `${capitalize(q.type)} • ${capitalize(nxt.difficulty || "medium")}`;
  $("q-text").textContent = q.text;
  $("q-progress-text").textContent = `${nxt.question_number} / ${nxt.total}`;
  $("q-progress-bar").style.width = Math.min(100, (nxt.question_number / nxt.total) * 100) + "%";

  const fu = $("followup-note");
  if (nxt.is_follow_up) {
    fu.hidden = false;
    $("conn-question").textContent = state.history.length ? truncate(state.history[state.history.length - 1].q, 48) : "Previous answer";
  } else {
    fu.hidden = true;
  }

  $("answer-input").value = "";
  setError("", $("answer-error"));
  $("answer-loading").hidden = true;
  $("submit-btn").disabled = false;
  $("skip-btn").disabled = false;

  // mark current category
  const cat = catFor(q.type);
  state.cats[cat] = "current";
  // mark all previously-answered as done
  state.history.forEach((h) => { state.cats[catFor(h.q.type)] = "done"; });
  renderProgressPanel();
}

function truncate(s, n) { s = s || ""; return s.length > n ? s.slice(0, n) + "…" : s; }

function appendHistory(item) {
  const container = ensureHistoryContainer();
  const div = document.createElement("div");
  div.className = "qa-item";
  div.innerHTML = `<p class="q">${escapeHtml(item.q.text)}</p><p class="a">${escapeHtml(item.a)}</p>`;
  container.appendChild(div);
}
function ensureHistoryContainer() {
  let c = $("interview-history");
  if (!c) {
    c = document.createElement("div");
    c.id = "interview-history";
    c.className = "conversation";
    $("question-panel").parentNode.insertBefore(c, $("question-panel"));
  }
  return c;
}

async function submitAnswer() {
  if (state.busy || !state.next || !state.next.question) return;
  const answer = $("answer-input").value.trim();
  if (!answer) { setError("Please type an answer before submitting.", $("answer-error")); return; }

  state.busy = true;
  $("submit-btn").disabled = true;
  $("skip-btn").disabled = true;
  $("answer-loading").hidden = false;
  $("answer-loading-text").textContent = "Analyzing your answer…";

  const question = state.next.question;
  try {
    const data = await api(`/api/interview/${state.sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: question.id, answer }),
    });
    state.history.push({ q: question, a: answer, isFollow: !!state.next.is_follow_up });
    appendHistory({ q: question, a: answer });
    state.next = data.next;
    $("answer-loading-text").textContent = "Preparing the next question…";
    await delay(700);
    if (data.report_ready) renderFinishBanner();
    else renderNextQuestion();
  } catch (err) {
    setError(err.message, $("answer-error"));
  } finally {
    state.busy = false;
    $("answer-loading").hidden = true;
    $("submit-btn").disabled = false;
    $("skip-btn").disabled = false;
  }
}

async function skipQuestion() {
  if (state.busy || !state.next || !state.next.question) return;
  state.busy = true;
  $("submit-btn").disabled = true;
  $("skip-btn").disabled = true;
  const question = state.next.question;
  try {
    const data = await api(`/api/interview/${state.sessionId}/skip`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: question.id }),
    });
    state.history.push({ q: question, a: "(skipped)", isFollow: false });
    appendHistory({ q: question, a: "(skipped)" });
    state.next = data.next;
    if (state.next && state.next.question) renderNextQuestion();
    else renderFinishBanner();
  } catch (err) {
    toast(err.message);
  } finally {
    state.busy = false;
    $("submit-btn").disabled = false;
    $("skip-btn").disabled = false;
  }
}

function renderFinishBanner() {
  const qp = $("question-panel");
  const ap = $("answer-panel");
  qp.hidden = true;
  ap.hidden = true;
  qp.innerHTML = `<div style="text-align:center;padding:40px 0"><p style="color:var(--text-dim);margin-bottom:18px">You answered every question. Ready for your report?</p><button class="btn btn-primary" id="finish-now">View Report</button></div>`;
  qp.hidden = false;
  $("finish-now").addEventListener("click", finishInterview);
}

/* ================================================================
   END MODAL
   ================================================================ */
function openEndModal() { $("modal-end").hidden = false; }
function closeEndModal() { $("modal-end").hidden = true; }

async function finishInterview() {
  closeEndModal();
  clearInterval(state.timerId);
  $("question-panel").hidden = true;
  $("answer-panel").hidden = true;
  showAnalyzing();
  try {
    const data = await api(`/api/interview/${state.sessionId}/finish`, { method: "POST" });
    state.report = data.report;
    state.session = await api(`/api/interview/${state.sessionId}`);
    localStorage.removeItem("moc_session_id");
    saveHistory();
    await delay(1100);
    showReport();
  } catch (err) {
    toast(err.message);
    showView("interview");
  }
}

function showAnalyzing() {
  const stages = [
    { t: "Reviewing answers", s: "active" },
    { t: "Evaluating technical knowledge", s: "pending" },
    { t: "Evaluating communication", s: "pending" },
    { t: "Identifying strengths and weaknesses", s: "pending" },
    { t: "Generating personalized feedback", s: "pending" },
  ];
  $("an-stages").innerHTML = stages
    .map((x, i) => `<li class="${i === 0 ? "active" : ""}"><span>${x.t}</span></li>`)
    .join("");
  // simple sequential fill
  const lis = $("an-stages").querySelectorAll("li");
  let i = 0;
  const iv = setInterval(() => {
    if (i > 0) lis[i - 1].classList.replace("active", "done");
    if (i < lis.length) { lis[i].classList.add("active"); i++; }
    else clearInterval(iv);
  }, 450);
  showView("analyzing");
}

/* ================================================================
   REPORT
   ================================================================ */
function showReport() {
  const r = state.report;
  const s = state.session || {};
  $("score-ring").style.setProperty("--pct", r.overall_score);
  $("overall-score").textContent = Math.round(r.overall_score);
  $("score-label").textContent = scoreLabel(r.overall_score);

  const metrics = [
    ["Technical Knowledge", r.technical_score],
    ["Communication", r.communication_score],
    ["Problem Solving", r.problem_solving_score],
    ["Behavioral", r.behavioral_score],
    ["Resume Relevance", r.resume_relevance],
  ];
  $("score-cards").innerHTML = metrics.map(([label, val]) => `
    <div class="glass-card score-card">
      <div class="sc-label">${label}</div>
      <div class="sc-ring" data-score="${val}" style="--pct:${val}"></div>
      <div class="sc-value">${val}<span style="font-size:13px;color:var(--text-faint)">/100</span></div>
    </div>`).join("");

  $("chart").innerHTML = metrics.map(([label, val]) => `
    <div class="bar-row">
      <div class="b-label">${label}</div>
      <div class="b-track"><div class="b-fill" style="width:${val}%"></div></div>
      <div class="b-val">${val}</div>
    </div>`).join("");

  renderListUL("report-strengths", r.strengths);
  renderListUL("report-weaknesses", r.weaknesses);
  renderListUL("report-did-well", r.strengths);
  renderListUL("report-improve", r.improvements);

  $("report-better-list").innerHTML = (r.better_answers || [])
    .map((b) => `<li><b>${escapeHtml(b.question)}</b><br><span style="color:var(--text-faint)">${escapeHtml(b.your_answer || "")}</span><br><span style="color:var(--accent-2)">${escapeHtml(b.better_answer || "")}</span></li>`)
    .join("") || "<li>No suggestions available.</li>";

  renderQuestionAnalysis(r.question_results || []);
  renderPractice(r.recommended_practice || [], r.weaknesses || []);

  showView("report");
}

function scoreLabel(s) {
  if (s >= 80) return "Strong Performance";
  if (s >= 65) return "Solid Performance";
  if (s >= 50) return "Getting There";
  return "Keep Practicing";
}

function renderListUL(id, items) {
  $(id).innerHTML = (items && items.length)
    ? items.map((i) => `<li>${escapeHtml(i)}</li>`).join("")
    : "<li>None recorded.</li>";
}

function renderQuestionAnalysis(results) {
  const container = $("question-analysis");
  if (!results.length) { container.innerHTML = "<p style='color:var(--text-dim)'>No answered questions.</p>"; return; }
  container.innerHTML = results.map((item, idx) => {
    const dims = (state.session && state.session.answers) || [];
    const ans = dims.find((a) => a.question_id === item.question.id);
    let strengths = "", improvements = "";
    if (ans && ans.dimensions) {
      const entries = Object.entries(ans.dimensions).sort((a, b) => b[1] - a[1]);
      strengths = entries.slice(0, 2).map((e) => `<li>${escapeHtml(e[0])} (${e[1]}/10)</li>`).join("");
      improvements = entries.slice(-2).reverse().map((e) => `<li>${escapeHtml(e[0])} (${e[1]}/10)</li>`).join("");
    }
    const better = (state.report.better_answers || []).find((b) => b.question === item.question.text);
    return `
    <div class="qa-item-card${idx === 0 ? " open" : ""}">
      <div class="qa-head">
        <span class="chev material-symbols-outlined">expand_more</span>
        <span class="qa-score ${scoreClass(item.score)}">${item.score.toFixed(1)}</span>
        <span class="qa-qtext">${escapeHtml(item.question.text)}</span>
      </div>
      <div class="qa-body">
        <p class="qa-answer"><b style="color:var(--text-dim)">Your answer:</b> ${escapeHtml(item.answer)}</p>
        <p class="qa-eval"><b style="color:var(--text-dim)">AI evaluation:</b> ${escapeHtml(item.evaluation || "")}</p>
        <div class="qa-sections">
          <div><b>Strengths</b><ul>${strengths || "<li>—</li>"}</ul></div>
          <div><b>Improvements</b><ul>${improvements || "<li>—</li>"}</ul></div>
        </div>
        ${better ? `<div class="better-box"><div class="bb-label">Stronger Answer</div><div class="bb-yours">${escapeHtml(item.answer)}</div><div class="bb-better">${escapeHtml(better.better_answer)}</div></div>` : ""}
      </div>
    </div>`;
  }).join("");

  container.querySelectorAll(".qa-head").forEach((h) =>
    h.addEventListener("click", () => h.parentElement.classList.toggle("open"))
  );
}

function renderPractice(items, weaknesses) {
  const grid = $("practice-grid");
  if (!items.length) { grid.innerHTML = "<p style='color:var(--text-dim)'>No recommendations.</p>"; return; }
  grid.innerHTML = items.slice(0, 6).map((topic, i) => `
    <div class="practice-item">
      <p class="pi-title">${escapeHtml(topic)}</p>
      <p class="pi-why">${escapeHtml(weaknesses[i] || "Targeted practice to sharpen this area.")}</p>
      <div class="pi-foot">
        <span class="chip">Mixed</span>
        <button class="btn btn-ghost sm" data-practice>Practice</button>
      </div>
    </div>`).join("");
  grid.querySelectorAll("[data-practice]").forEach((b) =>
    b.addEventListener("click", () => toast("Practice mode coming soon."))
  );
}

/* ================================================================
   HISTORY + DASHBOARD
   ================================================================ */
function saveHistory() {
  try {
    const r = state.report;
    const hist = loadHistory();
    hist.unshift({
      role: ($("pv-role").textContent || "Interview"),
      difficulty: getVal("diff") || "medium",
      date: new Date().toLocaleDateString(),
      score: Math.round(r.overall_score),
      type: "Mixed",
    });
    localStorage.setItem("moc_history", JSON.stringify(hist.slice(0, 12)));
  } catch (_) {}
}
function loadHistory() {
  try { return JSON.parse(localStorage.getItem("moc_history") || "[]"); }
  catch (_) { return []; }
}

function showDashboard() {
  const hist = loadHistory();
  if (!hist.length) {
    $("stat-avg").textContent = "0";
    $("stat-sessions").textContent = "0";
    $("stat-best").textContent = "0";
    $("stat-answered").textContent = "0";
    $("recent-list").innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">inbox</span><h3>No interviews yet</h3><p>Start your first AI interview and begin tracking your progress.</p><button class="btn btn-primary" id="dash-empty-start">Start Interview</button></div>`;
    $("dash-empty-start").addEventListener("click", goToUpload);
    $("trend-chart").innerHTML = "";
    $("weak-chips").innerHTML = "";
    $("dash-practice").innerHTML = "";
    showView("dashboard");
    return;
  }

  const scores = hist.map((h) => h.score);
  $("stat-avg").textContent = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  $("stat-sessions").textContent = hist.length;
  $("stat-best").textContent = Math.max(...scores);
  $("stat-answered").textContent = hist.length * 10;

  $("recent-list").innerHTML = hist.map((h) => `
    <div class="recent-row">
      <div>
        <div class="recent-role">${escapeHtml(h.role)}</div>
        <div class="recent-meta">${escapeHtml(h.date)} · ${capitalize(h.difficulty)} · ${h.type}</div>
      </div>
      <div class="recent-score ${h.score >= 70 ? "good" : "avg"}">${h.score}</div>
    </div>`).join("");

  const trend = hist.slice(0, 6).reverse();
  const max = Math.max(...scores);
  $("trend-chart").innerHTML = trend.map((h) => `
    <div class="trend-col"><div class="tc-bar" style="height:${Math.max(8, (h.score / 100) * 140)}px"></div><div class="tc-lbl">${h.score}</div></div>`).join("");

  const weak = (state.report && state.report.weaknesses) || ["Communication", "System Design", "Behavioral Questions"];
  $("weak-chips").innerHTML = weak.slice(0, 5).map((w) => `<span class="chip">${escapeHtml(w)}</span>`).join("");
  $("dash-practice").innerHTML = ((state.report && state.report.recommended_practice) || ["Behavioral Interview Questions", "System Design Basics", "Coding Patterns"])
    .slice(0, 4).map((p) => `<div class="practice-item"><p class="pi-title">${escapeHtml(p)}</p><p class="pi-why">Personalized to your last session.</p><button class="btn btn-ghost sm" data-practice>Practice</button></div>`).join("");
  $("dash-practice").querySelectorAll("[data-practice]").forEach((b) =>
    b.addEventListener("click", () => toast("Practice mode coming soon."))
  );
  showView("dashboard");
}

/* ================================================================
   Restore
   ================================================================ */
async function restoreSession() {
  const sid = localStorage.getItem("moc_session_id");
  if (!sid) return;
  try {
    const data = await api(`/api/interview/${sid}`);
    state.sessionId = data.id;
    state.resume = data.resume || null;
    state.session = data;
    if (data.status === "completed" && data.report) {
      state.report = data.report;
      showReport();
      return;
    }
    if (data.status === "in_progress" || (data.question_order && data.question_order.length)) {
      // render any prior answers as history
      (data.answers || []).forEach((a) => {
        const q = (data.questions || []).find((x) => x.id === a.question_id);
        if (!q) return;
        if (a.skipped) state.history.push({ q, a: "(skipped)", isFollow: false });
        else state.history.push({ q, a: a.answer, isFollow: false });
      });
      await api(`/api/interview/${sid}/next`).then((d) => { state.next = d.next; });
      state.durationMs = 1200000;
      showInterview();
      return;
    }
    renderAnalysis();
    showView("analysis");
  } catch (_) {
    localStorage.removeItem("moc_session_id");
  }
}

/* ================================================================
   Reset
   ================================================================ */
function resetAll() {
  localStorage.removeItem("moc_session_id");
  state.sessionId = null;
  state.resume = null;
  state.summary = "";
  state.next = null;
  state.report = null;
  state.session = null;
  state.history = [];
  state.cats = {};
  clearInterval(state.timerId);
  // reset upload view
  $("dropzone").hidden = false;
  $("file-card").hidden = true;
  $("ai-processing").hidden = true;
  $("continue-btn").hidden = true;
  setError("", $("upload-error"));
  $("resume-input").value = "";
  showView("landing");
}

/* ================================================================
   Boot / events
   ================================================================ */
function bindEvents() {
  // landing
  $("landing-start").addEventListener("click", goToUpload);
  $("landing-upload").addEventListener("click", goToUpload);
  $("landing-cta").addEventListener("click", goToUpload);
  $("get-started-btn").addEventListener("click", goToUpload);
  $("drawer-get-started").addEventListener("click", () => { $("mobile-drawer").hidden = true; goToUpload(); });
  $("signin-btn").addEventListener("click", () => toast("Sign in coming soon."));
  $("drawer-signin").addEventListener("click", () => { $("mobile-drawer").hidden = true; toast("Sign in coming soon."); });

  // nav links / logo
  $$('[data-nav-home]').forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); showView("landing"); }));
  $$('.nav-links a[href^="#"], .footer-cols a[href^="#"]').forEach((a) =>
    a.addEventListener("click", (e) => { e.preventDefault(); scrollToSection(a.getAttribute("href").slice(1)); })
  );
  $("menu-btn").addEventListener("click", () => { $("mobile-drawer").hidden = !$("mobile-drawer").hidden; });

  // upload
  $("resume-input").addEventListener("change", () => {
    if ($("resume-input").files[0]) analyzeResume($("resume-input").files[0]);
  });
  const dz = $("dropzone");
  ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("dragover"); }));
  ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("dragover"); }));
  dz.addEventListener("drop", (e) => { if (e.dataTransfer.files[0]) analyzeResume(e.dataTransfer.files[0]); });
  $("remove-file").addEventListener("click", () => { $("file-card").hidden = true; $("dropzone").hidden = false; $("resume-input").value = ""; });
  $("continue-btn").addEventListener("click", () => { renderAnalysis(); showView("analysis"); setSteps("analysis"); });
  $("use-sample") && $("use-sample").addEventListener("click", () => {});
  $("analysis-continue").addEventListener("click", () => { showView("setup"); setSteps("setup"); buildSetup(); });

  // setup
  $("generate-btn").addEventListener("click", generateInterview);

  // interview
  $("submit-btn").addEventListener("click", submitAnswer);
  $("skip-btn").addEventListener("click", skipQuestion);
  $("clear-btn").addEventListener("click", () => ($("answer-input").value = ""));
  $("mic-btn").addEventListener("click", () => toast("Voice input coming soon."));
  $("exit-interview").addEventListener("click", openEndModal);

  // modal
  $("modal-continue").addEventListener("click", closeEndModal);
  $("modal-end").addEventListener("click", finishInterview);

  // report actions
  $("retry-btn").addEventListener("click", resetAll);
  $("another-btn").addEventListener("click", resetAll);
  $("weak-btn").addEventListener("click", showDashboard);
  $("dashboard-btn").addEventListener("click", showDashboard);
  $("download-btn").addEventListener("click", () => window.print());

  // dashboard
  $("dash-start").addEventListener("click", goToUpload);

  // Ctrl/Cmd+Enter to submit
  $("answer-input").addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); submitAnswer(); }
  });
}

async function boot() {
  $("year").textContent = new Date().getFullYear();
  initNeural();
  bindEvents();
  try {
    const health = await api("/api/health");
    state.aiMode = health.ai_mode || "mock";
    const badge = $("mode-badge");
    if (badge) { badge.textContent = state.aiMode === "openai" ? "AI online" : "AI mock"; badge.classList.toggle("online", state.aiMode === "openai"); }
  } catch (_) {}
  restoreSession();
}

document.addEventListener("DOMContentLoaded", boot);
