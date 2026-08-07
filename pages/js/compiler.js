// In-browser strict compile + run, replacing examshell/compiler.py +
// examshell/runner.py's subprocess/gcc pipeline with the Wasmer JS SDK
// running the real `clang/clang` package from the Wasmer registry
// (wasm32-wasi), so GitHub Pages (static-only hosting, no server-side gcc)
// can still do a real, strict compile.
//
// Pattern verified against wasmerio/wasmer-js's own examples
// (examples/clang-cdn and examples/cdn-coi-serviceworker), which is also
// where pages/coi-serviceworker.js comes from: @wasmer/sdk needs
// SharedArrayBuffer / cross-origin isolation, which requires COOP/COEP
// response headers that GitHub Pages cannot be configured to send, hence
// the service-worker shim registered in index.html.
//
// Known limitation: the SDK doesn't expose a way to forcibly kill a running
// WASI instance, so a genuine infinite loop in student code can't be
// hard-killed the way the CLI's subprocess timeout can (see runner.py). A
// timed-out test is reported to the student as a timeout either way, but
// the underlying computation may keep running in the SDK's worker pool.

import { findForbiddenCalls } from "./forbidden.js";

const SDK_URL = "https://unpkg.com/@wasmer/sdk@0.10.0/dist/index.mjs";
const CLANG_PACKAGE = "clang/clang";

export const CFLAGS = ["-Wall", "-Wextra", "-Werror", "-std=gnu99"];

let sdkModulePromise = null;
let initPromise = null;
let clangPromise = null;

function loadSdk() {
  if (!sdkModulePromise) sdkModulePromise = import(SDK_URL);
  return sdkModulePromise;
}

async function ensureReady(onStatus) {
  const sdk = await loadSdk();
  if (!initPromise) {
    onStatus?.("initialisation du compilateur (premier chargement, peut prendre un moment)...");
    initPromise = sdk.init();
  }
  await initPromise;
  if (!clangPromise) {
    onStatus?.("téléchargement de clang...");
    clangPromise = sdk.Wasmer.fromRegistry(CLANG_PACKAGE);
  }
  return { sdk, clang: await clangPromise };
}

async function runTest(sdk, wasmBytes, test) {
  const timeoutSeconds = test.timeout ?? 5;
  let instance;
  try {
    const example = await sdk.Wasmer.fromFile(wasmBytes);
    instance = await example.entrypoint.run({
      args: test.argv,
      stdin: test.stdin ?? undefined,
    });
  } catch (err) {
    return { ok: false, actualStdout: "", error: `crashed while starting: ${err}` };
  }

  const timedOut = Symbol("timeout");
  let result;
  try {
    result = await Promise.race([
      instance.wait(),
      new Promise((resolve) => setTimeout(() => resolve(timedOut), timeoutSeconds * 1000)),
    ]);
  } catch (err) {
    return { ok: false, actualStdout: "", error: `crashed: ${err}` };
  }

  if (result === timedOut) {
    return {
      ok: false,
      actualStdout: "",
      error: `timeout (> ${timeoutSeconds}s), possible infinite loop`,
    };
  }

  const output = result;
  if (output.code < 0) {
    return { ok: false, actualStdout: "", error: `crashed (exit code ${output.code})` };
  }

  const actual = output.stdout;
  return { ok: actual === test.expectedStdout, actualStdout: actual };
}

/**
 * Compile `studentSource` for `exercise` (forbidden-function check, then a
 * strict clang compile with the exercise's harness if any) and, on success,
 * run every test case. Mirrors Session.run_tests()'s result shape:
 * one of `{ forbiddenCalls }`, `{ compileError }`, or `{ outcomes }`.
 */
export async function compileAndTest(exercise, studentSource, { onStatus } = {}) {
  const forbiddenCalls = findForbiddenCalls(studentSource, exercise.allowedFunctions);
  if (forbiddenCalls.length) {
    return { forbiddenCalls };
  }

  const { sdk, clang } = await ensureReady(onStatus);
  const { Directory } = sdk;

  const project = new Directory();
  await project.writeFile(exercise.filename, studentSource);
  const sourceFiles = [exercise.filename];
  if (exercise.type === "function") {
    await project.writeFile("_harness.c", exercise.harness);
    sourceFiles.push("_harness.c");
  }

  onStatus?.("compilation...");
  let compileOutput;
  try {
    const compileInstance = await clang.entrypoint.run({
      args: [...CFLAGS, ...sourceFiles.map((f) => `/project/${f}`), "-o", "/project/a.out.wasm"],
      mount: { "/project": project },
    });
    compileOutput = await compileInstance.wait();
  } catch (err) {
    return { compileError: String(err) };
  }
  if (!compileOutput.ok) {
    return { compileError: compileOutput.stderr };
  }

  const wasmBytes = await project.readFile("a.out.wasm");

  onStatus?.("exécution des tests...");
  const outcomes = [];
  for (const test of exercise.tests) {
    const outcome = await runTest(sdk, wasmBytes, test);
    outcomes.push({ test, ...outcome });
  }
  return { outcomes };
}
