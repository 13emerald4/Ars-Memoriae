import fs from 'node:fs';
import { deepStrictEqual } from 'node:assert';
import { createRequire } from 'node:module';
import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

// Node runs TypeScript by stripping the types, so `enum`, `namespace` and
// constructor parameter properties (`constructor(private x: number)`) fail to
// parse unless type transformation is switched on as well.
const NODE_RUN_FLAGS = ['--no-warnings'];
if (process.allowedNodeEnvironmentFlags.has('--experimental-transform-types')) {
  NODE_RUN_FLAGS.push('--experimental-transform-types');
}

// --- Optional type checking -------------------------------------------------
// Stripping types means a wrongly typed answer runs (and passes) like any
// other. A card that sets `type_check` is also checked with the TypeScript
// compiler, in strict mode, together with its `type_tests`: lines such as
//   // @ts-expect-error: "b" is not a key of the items
//   pluck([{ a: 1 }], "b");
// that only compile cleanly when the answer's types are as tight as asked.

const WORKER_DIR = path.dirname(fileURLToPath(import.meta.url));
const BACKEND_DIR = path.resolve(WORKER_DIR, '..', '..');

function loadTypeScript() {
  const req = createRequire(import.meta.url);
  // The backend has no node_modules of its own; the frontend's toolchain
  // already installs the compiler.
  for (const base of [BACKEND_DIR, path.join(BACKEND_DIR, '..', 'frontend')]) {
    try {
      return req(req.resolve('typescript', { paths: [base] }));
    } catch {}
  }
  return null;
}

// Node's globals the answers may use. The checker loads only the ES library,
// not the DOM or @types/node, so these are declared by hand.
const RUNNER_GLOBALS = `
declare var console: {
  log(...data: any[]): void; error(...data: any[]): void;
  warn(...data: any[]): void; info(...data: any[]): void;
};
declare function setTimeout(handler: (...args: any[]) => void, timeout?: number, ...args: any[]): number;
declare function clearTimeout(id: number | undefined): void;
declare function queueMicrotask(callback: () => void): void;
declare function structuredClone<T>(value: T): T;
`;

function typeCheck(code, typeTests) {
  const ts = loadTypeScript();
  if (!ts) return { available: false, errors: [] };

  const codeLines = code.split('\n').length;
  const source = typeTests ? `${code}\n${typeTests}` : code;
  const files = { 'solution.ts': source, 'runner-globals.d.ts': RUNNER_GLOBALS };
  const options = {
    strict: true,
    noEmit: true,
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ESNext,
    // Each answer is its own module, so a top-level `const name` does not
    // collide with a global of the same name.
    moduleDetection: ts.ModuleDetectionKind.Force,
    lib: ['lib.es2024.d.ts'],
    types: [],
    skipLibCheck: true,
  };
  const host = ts.createCompilerHost(options, true);
  const getSourceFile = host.getSourceFile.bind(host);
  const fileExists = host.fileExists.bind(host);
  const readFile = host.readFile.bind(host);
  host.getSourceFile = (name, version, ...rest) =>
    name in files ? ts.createSourceFile(name, files[name], version, true) : getSourceFile(name, version, ...rest);
  host.fileExists = (name) => name in files || fileExists(name);
  host.readFile = (name) => (name in files ? files[name] : readFile(name));

  const program = ts.createProgram(Object.keys(files), options, host);
  const sourceLines = source.split('\n');
  const errors = ts
    .getPreEmitDiagnostics(program)
    .filter((d) => d.category === ts.DiagnosticCategory.Error)
    .map((d) => {
      const message = ts.flattenDiagnosticMessageText(d.messageText, ' ');
      if (!d.file || d.file.fileName !== 'solution.ts' || d.start === undefined) {
        return { where: 'code', line: null, message, text: '' };
      }
      const line = d.file.getLineAndCharacterOfPosition(d.start).line;
      if (line < codeLines) {
        return { where: 'code', line: line + 1, message, text: sourceLines[line].trim() };
      }
      // An unused @ts-expect-error means the answer accepts a call it should
      // reject; show that call, and the directive's reason, not the bare TS text.
      const text = sourceLines[line].trim();
      if (/@ts-expect-error/.test(text) && /Unused '@ts-expect-error'/.test(message)) {
        const reason = text.replace(/^\/\/\s*@ts-expect-error:?\s*/, '');
        const call = (sourceLines[line + 1] || '').trim();
        return {
          where: 'type_test',
          line: null,
          message: `Your types accept \`${call}\`, which should be a type error${reason ? ` (${reason})` : ''}.`,
          text: call,
        };
      }
      return { where: 'type_test', line: null, message: `${message} In: \`${text}\``, text };
    });
  return { available: true, errors };
}

function formatTypeErrors(errors) {
  const lines = errors.slice(0, 8).map((e) =>
    e.where === 'code' && e.line ? `Line ${e.line}: ${e.message}` : e.message
  );
  if (errors.length > 8) lines.push(`…and ${errors.length - 8} more`);
  return `TypeScript type check failed:\n${lines.join('\n')}`;
}

// Applies the type-check verdict to a finished run. Runtime results stay, so
// the learner still sees which tests passed, but the run is not "Accepted".
function withTypeResult(summary, typeResult) {
  if (!typeResult) return summary;
  if (!typeResult.available) return { ...summary, type_check: 'unavailable' };
  if (typeResult.errors.length === 0) return { ...summary, type_check: 'passed' };
  return {
    ...summary,
    type_check: 'failed',
    type_errors: typeResult.errors,
    status: summary.status === 'Compile Error' ? summary.status : 'Type Error',
    error: summary.status === 'Compile Error' ? summary.error : formatTypeErrors(typeResult.errors),
  };
}

function deepEqual(a, b) {
  if (a === b) return true;
  if (typeof a === 'number' && typeof b === 'number') {
    return Math.abs(a - b) < 1e-5;
  }
  try {
    deepStrictEqual(a, b);
    return true;
  } catch {
    return false;
  }
}

async function main() {
  let rawInput = '';
  try {
    rawInput = fs.readFileSync(0, 'utf-8');
  } catch (err) {
    process.stdout.write(JSON.stringify({
      status: 'Compile Error',
      passed_count: 0,
      total_count: 0,
      runtime_ms: 0,
      error: `Failed to read input payload: ${err.message}`,
      results: []
    }));
    return;
  }

  let payload;
  try {
    payload = JSON.parse(rawInput);
  } catch (err) {
    process.stdout.write(JSON.stringify({
      status: 'Compile Error',
      passed_count: 0,
      total_count: 0,
      runtime_ms: 0,
      error: `Invalid JSON payload: ${err.message}`,
      results: []
    }));
    return;
  }

  const code = payload.code || '';
  const testCode = payload.test_code || '';
  const testCases = payload.test_cases || [];
  const customEntrypoint = payload.custom_entrypoint;
  const typeResult = payload.type_check === true ? typeCheck(code, payload.type_tests || '') : null;

  // Intercept stdout / console
  let stdoutLogs = [];
  const originalLog = console.log;
  const originalError = console.error;
  const originalWarn = console.warn;
  const originalInfo = console.info;

  const hookConsole = () => {
    stdoutLogs = [];
    const pushLog = (...args) => {
      stdoutLogs.push(args.map(a => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' '));
    };
    console.log = pushLog;
    console.error = pushLog;
    console.warn = pushLog;
    console.info = pushLog;
  };

  const unhookConsole = () => {
    console.log = originalLog;
    console.error = originalError;
    console.warn = originalWarn;
    console.info = originalInfo;
  };

  // If no test cases AND no custom test code are provided, execute code directly and return stdout/errors
  if ((!testCases || testCases.length === 0) && !testCode) {
    const start = performance.now();
    hookConsole();
    let runtimeErr = null;

    // Use a temporary file to allow Node's native TypeScript execution
    const tempFile = `temp_run_${Date.now()}_${Math.random().toString(36).slice(2)}.ts`;
    try {
      fs.writeFileSync(tempFile, code, 'utf-8');
      // Import the module dynamically
      await import(`file://${process.cwd()}/${tempFile}`);
    } catch (err) {
      runtimeErr = err instanceof Error ? err.message : String(err);
    } finally {
      unhookConsole();
      try {
        if (fs.existsSync(tempFile)) fs.unlinkSync(tempFile);
      } catch {}
    }

    const elapsed = performance.now() - start;
    const captured = stdoutLogs.join('\n');

    process.stdout.write(JSON.stringify(withTypeResult({
      status: runtimeErr ? 'Runtime Error' : 'Accepted',
      passed_count: runtimeErr ? 0 : 1,
      total_count: 1,
      runtime_ms: Math.round(elapsed * 100) / 100,
      error: runtimeErr,
      results: [{
        test_index: 1,
        passed: !runtimeErr,
        stdout: captured,
        error: runtimeErr,
        runtime_ms: Math.round(elapsed * 100) / 100
      }]
    }, typeResult)));
    return;
  }

  // We have test cases. We write a runner wrapper script to execute in Node with TS type stripping.
  const tempRunnerFile = `temp_runner_${Date.now()}_${Math.random().toString(36).slice(2)}.ts`;
  
// Extract candidate function names from user code ahead of time
  const candidateFunctionNames = [...code.matchAll(/(?:function|const|let|var)\s+([a-zA-Z0-9_$]+)/g)]
    .map(m => m[1])
    .filter(name => !['Solution', '__deepEqual', 'describe', 'test', 'it', 'checkExpect', 'checkError', 'checkExpectExact', 'checkErrorExact', 'assertOk', 'assertErr', 'assertEquals', 'assertNotEquals', 'assertTrue', 'assertFalse', 'assertNull', 'assertNotNull', 'assertThrows', 'fail', 'expect'].includes(name));

  const harnessCode = `
import { deepStrictEqual } from 'node:assert';

${code}

function __deepEqual(a, b) {
  if (a === b) return true;
  if (typeof a === 'number' && typeof b === 'number') {
    return Math.abs(a - b) < 1e-5;
  }
  try {
    deepStrictEqual(a, b);
    return true;
  } catch {
    return false;
  }
}

// --- CPSC 210 / JUnit / Jest Test Framework Harness ---
const __studentResults = [];
const __testPromises = [];
let __currentGroup = '';

function describe(groupName, fn) {
  const prevGroup = __currentGroup;
  __currentGroup = groupName;
  try {
    const res = fn();
    if (res && typeof res.then === 'function') {
      return res.finally(() => { __currentGroup = prevGroup; });
    }
  } finally {
    __currentGroup = prevGroup;
  }
}

function test(testName, fn) {
  const fullName = __currentGroup ? (__currentGroup + ' > ' + testName) : testName;
  const p = (async () => {
    const t0 = performance.now();
    try {
      if (typeof fn === 'function') {
        await fn();
      }
      const t1 = performance.now();
      __studentResults.push({
        test_name: fullName,
        passed: true,
        error: null,
        runtime_ms: Math.round((t1 - t0) * 100) / 100
      });
    } catch (err) {
      const t1 = performance.now();
      const msg = err instanceof Error ? err.message : String(err);
      __studentResults.push({
        test_name: fullName,
        passed: false,
        error: msg,
        runtime_ms: Math.round((t1 - t0) * 100) / 100
      });
    }
  })();
  __testPromises.push(p);
  return p;
}
const it = test;

function assertEquals(expected, actual, message) {
  if (!__deepEqual(actual, expected)) {
    const prefix = message ? (message + ': ') : '';
    throw new Error(prefix + 'Expected ' + JSON.stringify(expected) + ', but got ' + JSON.stringify(actual));
  }
}

function assertNotEquals(unexpected, actual, message) {
  if (__deepEqual(actual, unexpected)) {
    const prefix = message ? (message + ': ') : '';
    throw new Error(prefix + 'Expected value NOT to equal ' + JSON.stringify(unexpected));
  }
}

function assertTrue(condition, message) {
  if (!condition) {
    throw new Error(message || 'Expected true, but got false');
  }
}

function assertFalse(condition, message) {
  if (condition) {
    throw new Error(message || 'Expected false, but got true');
  }
}

function assertNull(value, message) {
  if (value !== null) {
    throw new Error(message || ('Expected null, but got ' + JSON.stringify(value)));
  }
}

function assertNotNull(value, message) {
  if (value === null) {
    throw new Error(message || 'Expected non-null value, but got null');
  }
}

function checkExpect(actualThunk, expected) {
  return async () => {
    let actual;
    if (typeof actualThunk === 'function') {
      actual = await Promise.resolve(actualThunk());
    } else {
      actual = actualThunk;
    }

    // CPSC 210 rule: treats any { ok: false } as matching an expected error Result, without comparing error/message
    if (
      expected &&
      typeof expected === 'object' &&
      expected.ok === false &&
      actual &&
      typeof actual === 'object' &&
      actual.ok === false
    ) {
      return;
    }

    if (!__deepEqual(actual, expected)) {
      throw new Error(
        'checkExpect failed: expected ' + JSON.stringify(expected) + ', but got ' + JSON.stringify(actual)
      );
    }
  };
}

function checkExpectExact(actualThunk, expected) {
  return async () => {
    let actual;
    if (typeof actualThunk === 'function') {
      actual = await Promise.resolve(actualThunk());
    } else {
      actual = actualThunk;
    }
    if (!__deepEqual(actual, expected)) {
      throw new Error(
        'checkExpectExact failed: expected ' + JSON.stringify(expected) + ', but got ' + JSON.stringify(actual)
      );
    }
  };
}

function checkError(thunk) {
  return async () => {
    let threw = false;
    try {
      if (typeof thunk === 'function') {
        await Promise.resolve(thunk());
      }
    } catch {
      threw = true;
    }
    if (!threw) {
      throw new Error('checkError failed: expected function to throw an error, but it returned normally');
    }
  };
}

function checkErrorExact(thunk, expectedError) {
  return async () => {
    let threw = false;
    let thrownErr = null;
    try {
      if (typeof thunk === 'function') {
        await Promise.resolve(thunk());
      }
    } catch (e) {
      threw = true;
      thrownErr = e;
    }
    if (!threw) {
      throw new Error('checkErrorExact failed: expected function to throw an error, but it returned normally');
    }
    if (expectedError) {
      const msg = thrownErr instanceof Error ? thrownErr.message : String(thrownErr);
      if (typeof expectedError === 'string' && !msg.includes(expectedError)) {
        throw new Error('checkErrorExact failed: expected error containing "' + expectedError + '", but got "' + msg + '"');
      }
    }
  };
}

function assertOk(result, message) {
  if (!result || typeof result !== 'object' || result.ok !== true) {
    const prefix = message ? (message + ': ') : '';
    throw new Error(prefix + 'Expected Result to be Ok ({ ok: true, value: ... }), but got ' + JSON.stringify(result));
  }
  return result.value !== undefined ? result.value : result;
}

function assertErr(result, message) {
  if (!result || typeof result !== 'object' || result.ok !== false) {
    const prefix = message ? (message + ': ') : '';
    throw new Error(prefix + 'Expected Result to be Err ({ ok: false, error: ... }), but got ' + JSON.stringify(result));
  }
  return result.error !== undefined ? result.error : (result.message !== undefined ? result.message : result);
}

function assertThrows(fn, expectedError, message) {
  let threw = false;
  let thrownError = null;
  try {
    if (typeof fn === 'function') {
      const res = fn();
      if (res && typeof res.then === 'function') {
        return res.then(
          () => { throw new Error(message || 'Expected async function to throw, but it resolved normally'); },
          (e) => {
            if (expectedError) {
              const errText = e instanceof Error ? e.message : String(e);
              if (typeof expectedError === 'string' && !errText.includes(expectedError)) {
                throw new Error(message || ('Expected error containing "' + expectedError + '", but got "' + errText + '"'));
              }
            }
          }
        );
      }
    }
  } catch (e) {
    threw = true;
    thrownError = e;
  }
  if (!threw) {
    throw new Error(message || 'Expected function to throw an exception, but it returned normally');
  }
  if (expectedError) {
    const errText = thrownError instanceof Error ? thrownError.message : String(thrownError);
    if (typeof expectedError === 'string' && !errText.includes(expectedError)) {
      throw new Error(message || ('Expected error containing "' + expectedError + '", but got "' + errText + '"'));
    }
  }
}

function fail(message) {
  throw new Error(message || 'Test failed explicitly via fail()');
}

function expect(actual) {
  return {
    toBe(expected) {
      if (actual !== expected) {
        throw new Error('Expected ' + JSON.stringify(expected) + ', but got ' + JSON.stringify(actual));
      }
    },
    toEqual(expected) {
      if (!__deepEqual(actual, expected)) {
        throw new Error('Expected deep equal ' + JSON.stringify(expected) + ', but got ' + JSON.stringify(actual));
      }
    },
    toBeTruthy() {
      if (!actual) throw new Error('Expected truthy, but got ' + JSON.stringify(actual));
    },
    toBeFalsy() {
      if (actual) throw new Error('Expected falsy, but got ' + JSON.stringify(actual));
    },
    toBeOk() {
      assertOk(actual);
    },
    toBeErr() {
      assertErr(actual);
    },
    toThrow(expectedMsg) {
      if (typeof actual !== 'function') throw new Error('expect(fn).toThrow requires a function');
      assertThrows(actual, expectedMsg);
    },
    not: {
      toBe(expected) {
        if (actual === expected) throw new Error('Expected not ' + JSON.stringify(expected));
      },
      toEqual(expected) {
        if (__deepEqual(actual, expected)) throw new Error('Expected not to equal ' + JSON.stringify(expected));
      }
    }
  };
}

// Find callable entrypoint
let __fn = null;
let __instance = null;

${customEntrypoint ? `
if (typeof ${customEntrypoint} === 'function') {
  __fn = ${customEntrypoint};
}
` : `
if (typeof Solution === 'function') {
  try {
    __instance = new Solution();
    const props = Object.getOwnPropertyNames(Object.getPrototypeOf(__instance));
    const methods = props.filter(p => p !== 'constructor' && typeof __instance[p] === 'function');
    if (methods.length > 0) {
      __fn = __instance[methods[0]].bind(__instance);
    }
  } catch (e) {}
}

if (!__fn) {
  const __candidateNames = ${JSON.stringify(candidateFunctionNames)};
  for (const name of __candidateNames) {
    if (typeof eval('typeof ' + name) !== 'undefined') {
      try {
        const candidate = eval(name);
        if (typeof candidate === 'function') {
          __fn = candidate;
          break;
        }
      } catch (e) {}
    }
  }
}
`}

const __testCases = ${JSON.stringify(testCases)};
const __results = [];
let __passedCount = 0;
let __overallStatus = 'Accepted';

// JSON has no \`undefined\`, so a test case spells it {"$undefined": true},
// in an input (a missing argument or property) or as the expected value.
function __decodeSpecial(v) {
  if (Array.isArray(v)) return v.map(__decodeSpecial);
  if (v && typeof v === 'object') {
    const keys = Object.keys(v);
    if (keys.length === 1 && keys[0] === '$undefined' && v.$undefined === true) return undefined;
    const out = {};
    for (const k of keys) out[k] = __decodeSpecial(v[k]);
    return out;
  }
  return v;
}

for (let __i = 0; __i < __testCases.length; __i++) {
  const __tc = __testCases[__i];
  const __input = __decodeSpecial(__tc.input);
  const __expected = __decodeSpecial(__tc.expected);

  let __actual = null;
  let __err = null;
  let __threw = false;
  let __errText = '';
  let __passed = false;
  const __logs = [];
  // {"$throws": "text"} (or true): the call must throw or reject, with an
  // error whose "Name: message" contains the text.
  const __throwSpec = (__tc.expected && typeof __tc.expected === 'object' && !Array.isArray(__tc.expected)
    && Object.keys(__tc.expected).length === 1 && '$throws' in __tc.expected)
    ? __tc.expected.$throws
    : undefined;

  const __oldLog = console.log;
  const __oldErr = console.error;
  console.log = (...args) => __logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
  console.error = (...args) => __logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));

  const __t0 = performance.now();
  try {
    if (!__fn) {
      throw new Error('No callable function or Solution method found in code.');
    }

    let __res;
    if (typeof __input === 'object' && __input !== null && !Array.isArray(__input)) {
      const vals = Object.values(__input);
      if (__fn.length === 1 && Object.keys(__input).length > 1) {
        __res = __fn(__input);
      } else {
        __res = __fn(...vals);
      }
    } else if (Array.isArray(__input)) {
      __res = __fn(...__input);
    } else {
      __res = __fn(__input);
    }
    __actual = await Promise.resolve(__res);
  } catch (e) {
    __threw = true;
    __err = e instanceof Error ? e.message : String(e);
    __errText = e instanceof Error ? e.name + ': ' + e.message : String(e);
  } finally {
    console.log = __oldLog;
    console.error = __oldErr;
  }
  const __t1 = performance.now();
  const __runtime = Math.round((__t1 - __t0) * 100) / 100;

  if (__throwSpec !== undefined) {
    const __want = __throwSpec === true ? '' : String(__throwSpec);
    if (__threw) {
      __passed = __errText.includes(__want);
      __err = __passed ? null : 'Threw "' + __errText + '", expected an error containing "' + __want + '"';
    } else {
      __passed = false;
      __err = 'Expected an error' + (__want ? ' containing "' + __want + '"' : '') + ', but it returned ' + JSON.stringify(__actual);
    }
    if (__passed) {
      __passedCount++;
    } else if (__overallStatus === 'Accepted') {
      __overallStatus = 'Wrong Answer';
    }
  } else if (__err) {
    if (__overallStatus === 'Accepted') __overallStatus = 'Runtime Error';
    __passed = false;
  } else {
    __passed = __deepEqual(__actual, __expected);
    if (__passed) {
      __passedCount++;
    } else {
      if (__overallStatus === 'Accepted') __overallStatus = 'Wrong Answer';
    }
  }

  __results.push({
    test_index: __i + 1,
    passed: __passed,
    input: __tc.input,
    expected: __tc.expected,
    actual: __actual,
    stdout: __logs.join('\\n'),
    error: __err,
    runtime_ms: __runtime
  });
}

// Execute student-authored test suite if provided
${testCode ? `
try {
  const __initialCount = __studentResults.length;
  ${testCode}
  await Promise.all(__testPromises);
  if (__studentResults.length === __initialCount) {
    __studentResults.push({
      test_name: 'Top-Level Assertions',
      passed: true,
      error: null,
      runtime_ms: 1.0
    });
  }
} catch (err) {
  const msg = err instanceof Error ? err.message : String(err);
  __studentResults.push({
    test_name: 'Test Suite Execution',
    passed: false,
    error: msg,
    runtime_ms: 1.0
  });
}
` : ''}

const __studentPassed = __studentResults.filter(r => r.passed).length;
const __studentTotal = __studentResults.length;

if (__testCases.length === 0 && __studentTotal > 0) {
  __passedCount = __studentPassed;
  __overallStatus = __studentPassed === __studentTotal ? 'Accepted' : 'Wrong Answer';
} else if (__studentTotal > 0 && __studentPassed < __studentTotal) {
  if (__overallStatus === 'Accepted') {
    __overallStatus = 'Wrong Answer';
  }
}

const __summary = {
  status: __overallStatus,
  passed_count: __passedCount,
  total_count: __testCases.length > 0 ? __testCases.length : __studentTotal,
  runtime_ms: Math.round((__results.reduce((acc, r) => acc + r.runtime_ms, 0) + __studentResults.reduce((acc, r) => acc + r.runtime_ms, 0)) * 100) / 100,
  error: __overallStatus === 'Runtime Error' ? (__results.find(r => r.error)?.error || null) : null,
  results: __results,
  student_tests: __studentResults,
  student_passed_count: __studentPassed,
  student_total_count: __studentTotal
};

process.stdout.write(JSON.stringify(__summary));
`;

  try {
    fs.writeFileSync(tempRunnerFile, harnessCode, 'utf-8');
    const { execSync } = await import('node:child_process');
    const output = execSync(`"${process.execPath}" ${NODE_RUN_FLAGS.join(' ')} "${tempRunnerFile}"`, {
      encoding: 'utf-8',
      timeout: 5000,
      maxBuffer: 5 * 1024 * 1024
    });
    let summary = null;
    try {
      summary = JSON.parse(output);
    } catch {}
    process.stdout.write(summary ? JSON.stringify(withTypeResult(summary, typeResult)) : output);
  } catch (err) {
    const errorMsg = err.stderr ? err.stderr.toString() : err.message;
    process.stdout.write(JSON.stringify(withTypeResult({
      status: 'Compile Error',
      passed_count: 0,
      total_count: testCases.length,
      runtime_ms: 0,
      error: errorMsg.split('\n').slice(0, 5).join('\n'),
      results: testCases.map((tc, idx) => ({
        test_index: idx + 1,
        passed: false,
        input: tc.input,
        expected: tc.expected,
        actual: null,
        stdout: '',
        error: errorMsg.split('\n')[0] || 'Error',
        runtime_ms: 0
      }))
    }, typeResult)));
  } finally {
    try {
      if (fs.existsSync(tempRunnerFile)) fs.unlinkSync(tempRunnerFile);
    } catch {}
  }
}

main();
