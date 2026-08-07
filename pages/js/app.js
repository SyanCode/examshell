import { loadExercises, skeleton, byRank, loadSolution } from "./exercises.js";
import { Session, pickExercises, RANK_DURATION_MINUTES, RANK_EXERCISE_COUNT } from "./session.js";
import { compileAndTest } from "./compiler.js";

const app = document.getElementById("app");

const state = {
  exercises: null,
  loadError: null,
  view: "loading",
  session: null,
  mode: null, // "exam" | "practice"
  currentExId: null,
  running: false,
  statusText: "",
  revealedSolution: null, // { exId, code }
};

function visible(s, limit = 400) {
  const escaped = s.replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/\t/g, "\\t");
  return escaped.length > limit ? escaped.slice(0, limit) + "...(tronqué)" : escaped;
}

function formatTimer(secondsLeft) {
  const s = Math.max(0, Math.floor(secondsLeft));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

function goto(view, patch = {}) {
  Object.assign(state, { view }, patch);
  render();
}

// ---------------------------------------------------------------- top bar

function renderTopbar() {
  const bar = el("div", { id: "topbar" }, [
    el("span", { class: "title" }, "examshell"),
  ]);
  if (state.session) {
    bar.appendChild(el("span", {}, `— ${state.session.name}`));
  }
  bar.appendChild(el("span", { class: "spacer" }));
  if (state.session && state.session.durationMinutes != null) {
    const remaining = state.session.remainingSeconds();
    const timer = el(
      "span",
      { class: "timer" + (remaining <= 60 ? " low" : "") },
      `⏱ ${formatTimer(remaining)}`
    );
    bar.appendChild(timer);
  }
  if (state.session) {
    bar.appendChild(
      el("button", { onclick: () => confirmEndSession() }, state.mode === "exam" ? "Terminer l'examen" : "Retour au menu")
    );
  }
  return bar;
}

function confirmEndSession() {
  if (state.mode === "exam") {
    if (!confirm("Terminer l'examen maintenant ?")) return;
    goto("report");
  } else {
    state.session = null;
    state.mode = null;
    goto("menu");
  }
}

// ---------------------------------------------------------------- menu

function renderMenu() {
  const screen = el("div", { class: "screen" }, [
    el("h1", {}, "examshell"),
    el("p", {}, "Simulateur d'examen C, 100% dans le navigateur (compilation WebAssembly, aucun serveur)."),
    el(
      "button",
      { class: "menu-choice", onclick: () => goto("exam-setup") },
      [
        el("div", {}, "1) Examen chronométré"),
        el("div", { class: "desc" }, "Choisis un rank, un minuteur démarre, le score final est calculé."),
      ]
    ),
    el(
      "button",
      { class: "menu-choice", onclick: () => startPractice() },
      [
        el("div", {}, "2) Mode entraînement"),
        el("div", { class: "desc" }, "Aucun minuteur, tous les exercices, tentatives illimitées, solutions révélables."),
      ]
    ),
  ]);
  app.replaceChildren(screen);
}

function renderExamSetup() {
  const ranks = [...new Set([...state.exercises.values()].map((e) => e.rank))].sort();
  const screen = el("div", { class: "screen" }, [
    el("h1", {}, "Examen chronométré"),
    el("p", {}, "Choisis un rank :"),
    ...ranks.map((rank) => {
      const count = RANK_EXERCISE_COUNT[rank] ?? Math.min(4, byRank(state.exercises, rank).length);
      const duration = RANK_DURATION_MINUTES[rank] ?? 90;
      return el(
        "button",
        { class: "menu-choice", onclick: () => startExam(rank) },
        [
          el("div", {}, [el("span", { class: "rank-pill" }, `rank ${rank}`), `${count} exercices, ${duration} min`]),
        ]
      );
    }),
    el("button", { class: "secondary", onclick: () => goto("menu") }, "Retour"),
  ]);
  app.replaceChildren(screen);
}

function startExam(rank) {
  const chosen = pickExercises(state.exercises, rank);
  const duration = RANK_DURATION_MINUTES[rank] ?? 90;
  const name = `exam-rank${rank}-${new Date().toISOString().replace(/[:.]/g, "-")}`;
  state.session = new Session(chosen, duration, name);
  state.mode = "exam";
  goto("board");
}

function startPractice() {
  const all = [...state.exercises.values()].sort((a, b) => (a.rank - b.rank) || a.id.localeCompare(b.id));
  const name = `practice-${new Date().toISOString().replace(/[:.]/g, "-")}`;
  state.session = new Session(all, null, name);
  state.mode = "practice";
  goto("board");
}

// ---------------------------------------------------------------- board

function renderBoard() {
  const session = state.session;
  const board = el("div", { id: "board" });
  const list = el("ul");
  for (const exId of session.order) {
    const st = session.states.get(exId);
    const tagClass = st.attempts === 0 ? "pending" : st.passed ? "ok" : "ko";
    const tagText = st.attempts === 0 ? "—" : st.passed ? "OK" : "KO";
    const li = el(
      "li",
      { class: exId === state.currentExId ? "active" : "", onclick: () => openExercise(exId) },
      [
        el("span", { class: `tag ${tagClass}` }, tagText),
        el("div", { style: "flex:1" }, [
          el("div", { class: "ex-title" }, `${st.exercise.title}`),
          el("div", { class: "ex-summary" }, `rank ${st.exercise.rank} · ${st.summary()}`),
        ]),
      ]
    );
    list.appendChild(li);
  }
  board.appendChild(list);

  const workspace = el("div", { id: "workspace" });
  if (state.currentExId) {
    workspace.appendChild(renderEditor());
  } else {
    workspace.appendChild(
      el("div", { class: "screen" }, [
        el("h2", {}, session.name),
        el("p", {}, "Choisis un exercice dans la liste à gauche."),
      ])
    );
  }

  const wrap = el("div", { class: "workbench" }, [board, workspace]);
  app.replaceChildren(renderTopbar(), el("main", {}, wrap));
}

function openExercise(exId) {
  state.currentExId = exId;
  const st = state.session.states.get(exId);
  if (st.code === null) st.code = skeleton(st.exercise);
  state.revealedSolution = null;
  render();
}

// ---------------------------------------------------------------- editor

function renderEditor() {
  const session = state.session;
  const st = session.states.get(state.currentExId);
  const ex = st.exercise;

  const allowed = ex.allowedFunctions.length ? ex.allowedFunctions.join(", ") : "(aucune)";
  const statement = el("div", { class: "statement" }, [
    el("div", { class: "meta" }, `rank ${ex.rank} · ~${ex.timeMinutes} min · fichier : ${ex.filename}`),
    el("div", {}, ex.statement.trim()),
    ex.prototype ? el("div", { style: "margin-top:0.6rem" }, [el("b", {}, "Prototype : "), ex.prototype]) : null,
    el("div", { style: "margin-top:0.3rem" }, [el("b", {}, "Fonctions autorisées : "), allowed]),
  ]);

  const textarea = el("textarea", { id: "editor", spellcheck: "false" });
  textarea.value = st.code ?? skeleton(ex);
  textarea.addEventListener("input", () => {
    st.code = textarea.value;
  });

  const runBtn = el(
    "button",
    { class: "primary", disabled: state.running ? "true" : null, onclick: () => runExercise() },
    state.running ? "Compilation..." : "Compiler et tester"
  );
  const actions = el("div", { class: "editor-actions" }, [
    runBtn,
    el("span", { class: "status-line" }, state.statusText),
  ]);

  const container = el("div", {}, [statement, textarea, actions]);

  if (state.mode === "practice") {
    container.appendChild(
      el(
        "button",
        { class: "secondary", style: "margin-bottom:1rem", onclick: () => revealSolution(ex) },
        "Révéler la solution de référence"
      )
    );
    if (state.revealedSolution && state.revealedSolution.exId === ex.id) {
      container.appendChild(
        el("pre", { class: "statement" }, state.revealedSolution.code)
      );
    }
  }

  container.appendChild(renderResults(st));
  return container;
}

async function revealSolution(ex) {
  if (!confirm(`Révéler la solution de référence pour ${ex.id} ?`)) return;
  try {
    const code = await loadSolution(ex);
    state.revealedSolution = { exId: ex.id, code };
    render();
  } catch (err) {
    alert(`Impossible de charger la solution : ${err}`);
  }
}

async function runExercise() {
  const session = state.session;
  const st = session.states.get(state.currentExId);
  state.running = true;
  state.statusText = "préparation...";
  render();

  try {
    const result = await compileAndTest(st.exercise, st.code, {
      onStatus: (text) => {
        state.statusText = text;
        const line = document.querySelector(".status-line");
        if (line) line.textContent = text;
      },
    });
    session.recordAttempt(state.currentExId, result);
  } catch (err) {
    session.recordAttempt(state.currentExId, { compileError: `Erreur inattendue : ${err}` });
  }

  state.running = false;
  state.statusText = "";
  render();

  if (state.mode === "exam" && session.expired()) {
    goto("report");
  }
}

function renderResults(st) {
  const box = el("div", { id: "results" });
  if (st.attempts === 0) {
    return box;
  }
  const block = el("div", { class: "result-block" });

  if (st.forbiddenCalls.length) {
    block.appendChild(el("div", { class: "result-error" }, `FONCTION(S) INTERDITE(S) : ${st.forbiddenCalls.join(", ")}`));
    block.appendChild(el("p", {}, "Ton fichier appelle une fonction qui n'est pas dans la liste autorisée pour cet exercice."));
  } else if (st.compileError) {
    block.appendChild(el("div", { class: "result-error" }, "ÉCHEC DE LA COMPILATION"));
    block.appendChild(el("pre", {}, st.compileError.trim()));
  } else {
    st.outcomes.forEach((outcome, i) => {
      const argvRepr = outcome.test.argv.length ? outcome.test.argv.join(" ") : "(pas d'arguments)";
      const row = el("div", { class: "test-row" }, [
        el("span", { class: outcome.ok ? "ok" : "ko" }, outcome.ok ? "OK" : "KO"),
        el("span", {}, `test ${i + 1} : argv=(${argvRepr})`),
      ]);
      block.appendChild(row);
      if (!outcome.ok) {
        if (outcome.error) {
          block.appendChild(el("div", { class: "test-detail" }, outcome.error));
        } else {
          block.appendChild(el("div", { class: "test-detail" }, `attendu : ${visible(outcome.test.expectedStdout)}`));
          block.appendChild(el("div", { class: "test-detail" }, `obtenu :  ${visible(outcome.actualStdout)}`));
        }
      }
    });
    const tag = el(
      "div",
      { class: `final-tag ${st.passed ? "pass" : "fail"}` },
      `${st.exercise.id}: ${st.passed ? "RÉUSSI" : "ÉCHOUÉ"} (${st.testsPassed}/${st.testsTotal})`
    );
    block.appendChild(tag);
  }

  box.appendChild(block);
  return box;
}

// ---------------------------------------------------------------- report

function renderReport() {
  const session = state.session;
  const [passed, total] = session.score();
  const bannerClass = passed === total ? "pass" : passed === 0 ? "fail" : "partial";

  const rows = session.order.map((exId) => {
    const st = session.states.get(exId);
    return el("tr", {}, [
      el("td", {}, st.passed ? "✅" : "❌"),
      el("td", {}, st.exercise.title),
      el("td", {}, `rank ${st.exercise.rank}`),
      el("td", {}, st.summary()),
    ]);
  });

  const table = el("table", { class: "report" }, [
    el("thead", {}, el("tr", {}, [el("th", {}, ""), el("th", {}, "Exercice"), el("th", {}, "Rank"), el("th", {}, "Résultat")])),
    el("tbody", {}, rows),
  ]);

  const screen = el("div", { class: "screen" }, [
    el("h1", {}, state.mode === "exam" ? "Examen terminé" : "Résumé"),
    el("div", { class: `score-banner ${bannerClass}` }, `Score : ${passed}/${total} exercices entièrement réussis`),
    table,
    el("div", { style: "margin-top:1.2rem; display:flex; gap:0.6rem" }, [
      el("button", { class: "primary", onclick: () => downloadReport(session) }, "Télécharger le rapport (JSON)"),
      el("button", { class: "secondary", onclick: () => backToMenu() }, "Retour au menu"),
    ]),
  ]);
  app.replaceChildren(el("main", {}, screen));
}

function downloadReport(session) {
  const blob = new Blob([JSON.stringify(session.report(), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: `${session.name}-report.json` });
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function backToMenu() {
  state.session = null;
  state.mode = null;
  state.currentExId = null;
  goto("menu");
}

// ---------------------------------------------------------------- render

function render() {
  if (state.view === "menu") return renderMenu();
  if (state.view === "exam-setup") return renderExamSetup();
  if (state.view === "board") return renderBoard();
  if (state.view === "report") return renderReport();
  app.replaceChildren(el("p", { class: "loading" }, "..."));
}

// Tick the timer and auto-end an expired exam even if the student never
// triggers another render (e.g. they're just staring at the editor).
setInterval(() => {
  if (state.session && state.mode === "exam" && state.view !== "report") {
    if (state.session.expired()) {
      goto("report");
    } else if (state.view === "board") {
      const timerEl = document.querySelector("#topbar .timer");
      if (timerEl) {
        const remaining = state.session.remainingSeconds();
        timerEl.textContent = `⏱ ${formatTimer(remaining)}`;
        timerEl.classList.toggle("low", remaining <= 60);
      }
    }
  }
}, 1000);

async function main() {
  try {
    state.exercises = await loadExercises();
    goto("menu");
  } catch (err) {
    state.loadError = err;
    app.replaceChildren(
      el("div", { class: "screen" }, [
        el("h1", {}, "examshell"),
        el("div", { class: "error-banner" }, `Impossible de charger les exercices : ${err}`),
      ])
    );
  }
}

main();
