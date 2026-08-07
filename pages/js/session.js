// Port of examshell/session.py: exam/practice state, timer and scoring.
// Compiling and running tests happens elsewhere (js/compiler.js); this module
// only tracks the resulting state, same split as Session.run_tests() did
// around compiler.compile_student()/runner.run_all() in the CLI.

import { byRank } from "./exercises.js";

export const RANK_DURATION_MINUTES = { 1: 60, 2: 90, 3: 120 };
export const RANK_EXERCISE_COUNT = { 1: 3, 2: 4, 3: 4 };

export class ExerciseState {
  constructor(exercise) {
    this.exercise = exercise;
    this.attempts = 0;
    this.testsPassed = 0;
    this.testsTotal = 0;
    this.passed = false;
    this.compileError = null;
    this.forbiddenCalls = [];
    this.outcomes = [];
    this.code = null;
  }

  statusTag() {
    if (this.attempts === 0) return " ";
    return this.passed ? "OK" : "KO";
  }

  summary() {
    if (this.attempts === 0) return "not started";
    if (this.compileError) return "compile error";
    if (this.forbiddenCalls.length) return `forbidden: ${this.forbiddenCalls.join(", ")}`;
    return `${this.testsPassed}/${this.testsTotal} tests`;
  }
}

export class Session {
  constructor(exercises, durationMinutes, name) {
    this.states = new Map(exercises.map((e) => [e.id, new ExerciseState(e)]));
    this.order = exercises.map((e) => e.id);
    this.durationMinutes = durationMinutes;
    this.name = name;
    this.startTime = Date.now();
  }

  remainingSeconds() {
    if (this.durationMinutes == null) return null;
    const elapsed = (Date.now() - this.startTime) / 1000;
    return this.durationMinutes * 60 - elapsed;
  }

  expired() {
    const remaining = this.remainingSeconds();
    return remaining !== null && remaining <= 0;
  }

  ensureCode(exId, skeletonFn) {
    const state = this.states.get(exId);
    if (state.code === null) {
      state.code = skeletonFn(state.exercise);
    }
    return state.code;
  }

  /** Record the outcome of a compile+test attempt for one exercise. */
  recordAttempt(exId, result) {
    const state = this.states.get(exId);
    state.attempts += 1;

    if (result.forbiddenCalls && result.forbiddenCalls.length) {
      state.compileError = null;
      state.forbiddenCalls = result.forbiddenCalls;
      state.passed = false;
      state.testsTotal = state.exercise.tests.length;
      state.testsPassed = 0;
      state.outcomes = [];
      return state;
    }
    state.forbiddenCalls = [];

    if (result.compileError) {
      state.compileError = result.compileError;
      state.passed = false;
      state.testsTotal = state.exercise.tests.length;
      state.testsPassed = 0;
      state.outcomes = [];
      return state;
    }
    state.compileError = null;

    state.outcomes = result.outcomes;
    state.testsTotal = result.outcomes.length;
    state.testsPassed = result.outcomes.filter((o) => o.ok).length;
    state.passed = state.testsPassed === state.testsTotal;
    return state;
  }

  score() {
    let passed = 0;
    for (const st of this.states.values()) if (st.passed) passed++;
    return [passed, this.states.size];
  }

  report() {
    const results = {};
    for (const [exId, st] of this.states) {
      results[exId] = {
        title: st.exercise.title,
        rank: st.exercise.rank,
        attempts: st.attempts,
        passed: st.passed,
        tests_passed: st.testsPassed,
        tests_total: st.testsTotal,
        summary: st.summary(),
      };
    }
    return {
      name: this.name,
      started_at: this.startTime / 1000,
      duration_minutes: this.durationMinutes,
      results,
    };
  }
}

function sampleWithoutReplacement(pool, count) {
  const copy = [...pool];
  const result = [];
  for (let i = 0; i < count && copy.length; i++) {
    const idx = Math.floor(Math.random() * copy.length);
    result.push(copy.splice(idx, 1)[0]);
  }
  return result;
}

export function pickExercises(exercisesById, rank, count = null) {
  const pool = byRank(exercisesById, rank);
  const n = Math.min(count ?? RANK_EXERCISE_COUNT[rank] ?? Math.min(4, pool.length), pool.length);
  return sampleWithoutReplacement(pool, n);
}
