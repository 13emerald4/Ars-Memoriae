import fs from 'node:fs';
import { deepStrictEqual } from 'node:assert';
import { performance } from 'node:perf_hooks';
import vm from 'node:vm';

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
  const testCases = payload.test_cases || [];
  const customEntrypoint = payload.custom_entrypoint;

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

  // If no test cases are provided, execute code directly and return stdout/errors
  if (!testCases || testCases.length === 0) {
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

    process.stdout.write(JSON.stringify({
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
    }));
    return;
  }

  // We have test cases. We write a runner wrapper script to execute in Node with TS type stripping.
  const tempRunnerFile = `temp_runner_${Date.now()}_${Math.random().toString(36).slice(2)}.ts`;
  
  // Script structure:
  // 1. User code
  // 2. Export / extract entrypoint
  // 3. Loop over testcases, evaluate, capture output
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
  // Check common algorithmic function names or global declarations
  const globalKeys = Object.keys(globalThis);
  // Match functions declared in user code
  const declaredMatches = [...\`${code.replace(/`/g, '\\`').replace(/\\/g, '\\\\')}\`.matchAll(/(?:function|const|let|var)\\s+([a-zA-Z0-9_$]+)/g)];
  for (const m of declaredMatches) {
    const name = m[1];
    if (name !== 'Solution' && name !== '__deepEqual' && typeof eval('typeof ' + name) !== 'undefined') {
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

for (let __i = 0; __i < __testCases.length; __i++) {
  const __tc = __testCases[__i];
  const __input = __tc.input;
  const __expected = __tc.expected;

  let __actual = null;
  let __err = null;
  let __passed = false;
  const __logs = [];

  const __oldLog = console.log;
  const __oldErr = console.error;
  console.log = (...args) => __logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
  console.error = (...args) => __logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));

  const __t0 = performance.now();
  try {
    if (!__fn) {
      throw new Error('No callable function or Solution method found in code.');
    }

    if (typeof __input === 'object' && __input !== null && !Array.isArray(__input)) {
      const vals = Object.values(__input);
      if (__fn.length === 1 && Object.keys(__input).length > 1) {
        __actual = __fn(__input);
      } else {
        __actual = __fn(...vals);
      }
    } else if (Array.isArray(__input)) {
      __actual = __fn(...__input);
    } else {
      __actual = __fn(__input);
    }
  } catch (e) {
    __err = e instanceof Error ? e.message : String(e);
  } finally {
    console.log = __oldLog;
    console.error = __oldErr;
  }
  const __t1 = performance.now();
  const __runtime = Math.round((__t1 - __t0) * 100) / 100;

  if (__err) {
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
    input: __input,
    expected: __expected,
    actual: __actual,
    stdout: __logs.join('\\n'),
    error: __err,
    runtime_ms: __runtime
  });
}

const __summary = {
  status: __overallStatus,
  passed_count: __passedCount,
  total_count: __testCases.length,
  runtime_ms: Math.round(__results.reduce((acc, r) => acc + r.runtime_ms, 0) * 100) / 100,
  error: __overallStatus === 'Runtime Error' ? (__results.find(r => r.error)?.error || null) : null,
  results: __results
};

process.stdout.write(JSON.stringify(__summary));
`;

  try {
    fs.writeFileSync(tempRunnerFile, harnessCode, 'utf-8');
    const { execSync } = await import('node:child_process');
    const output = execSync(`"${process.execPath}" --no-warnings "${tempRunnerFile}"`, {
      encoding: 'utf-8',
      timeout: 5000,
      maxBuffer: 5 * 1024 * 1024
    });
    process.stdout.write(output);
  } catch (err) {
    const errorMsg = err.stderr ? err.stderr.toString() : err.message;
    process.stdout.write(JSON.stringify({
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
    }));
  } finally {
    try {
      if (fs.existsSync(tempRunnerFile)) fs.unlinkSync(tempRunnerFile);
    } catch {}
  }
}

main();
