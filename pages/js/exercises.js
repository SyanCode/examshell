// Loading exercises bundled by scripts/build_web_data.py into
// pages/data/exercises.json (mirrors examshell/exercises.py).

function normalizeExercise(data) {
  return {
    id: data.id,
    rank: data.rank,
    timeMinutes: data.time_minutes,
    title: data.title,
    type: data.type,
    filename: data.filename,
    statement: data.statement,
    allowedFunctions: data.allowed_functions || [],
    prototype: data.prototype ?? null,
    harness: data.harness ?? null,
    tests: (data.tests || []).map((t) => ({
      argv: t.argv || [],
      expectedStdout: t.expected_stdout,
      stdin: t.stdin ?? null,
      timeout: t.timeout ?? 5.0,
    })),
  };
}

export async function loadExercises(dataUrl = "data/exercises.json") {
  const res = await fetch(dataUrl);
  if (!res.ok) {
    throw new Error(`failed to load ${dataUrl}: HTTP ${res.status}`);
  }
  const list = await res.json();
  const byId = new Map();
  for (const data of list) {
    byId.set(data.id, normalizeExercise(data));
  }
  return byId;
}

export function skeleton(ex) {
  const allowed = ex.allowedFunctions.length ? ex.allowedFunctions.join(", ") : "(none)";
  const lines = ["#include <unistd.h>", ""];
  if (ex.type === "function") {
    lines.push(`/* ${ex.prototype} */`, "");
    lines.push(`/* Allowed functions: ${allowed} */`, "");
  } else {
    lines.push(`/* Allowed functions: ${allowed} */`, "");
    lines.push("int\tmain(void)", "{", "\treturn (0);", "}", "");
  }
  return lines.join("\n");
}

export function byRank(exercisesById, rank) {
  return [...exercisesById.values()]
    .filter((e) => e.rank === rank)
    .sort((a, b) => a.id.localeCompare(b.id));
}

export async function loadSolution(ex, dataDir = "data") {
  const res = await fetch(`${dataDir}/solutions/${ex.id}.c`);
  if (!res.ok) {
    throw new Error(`failed to load solution for ${ex.id}: HTTP ${res.status}`);
  }
  return res.text();
}
