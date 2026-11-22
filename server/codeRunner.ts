import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const SERVER_DIR = path.dirname(fileURLToPath(import.meta.url))
const TS_WORKER = path.join(SERVER_DIR, 'ts_sandbox_worker.mjs')

export interface RunCodePayload {
  code: string
  language?: string
  test_code?: string
  test_cases?: Array<{ input: unknown; expected: unknown }>
}

export interface RunCodeResult {
  status: string
  passed_count: number
  total_count: number
  runtime_ms: number
  error: string | null
  results: Array<{
    test_index: number
    passed: boolean
    input: unknown
    expected: unknown
    actual: unknown
    stdout: string
    error: string | null
    runtime_ms: number
  }>
  student_tests?: Array<{
    test_name: string
    passed: boolean
    error: string | null
    runtime_ms: number
  }>
  student_passed_count?: number
  student_total_count?: number
}

function runNodeTsWorker(payload: RunCodePayload): Promise<RunCodeResult> {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [TS_WORKER], {
      cwd: SERVER_DIR,
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 7000,
    })

    let stdout = ''
    let stderr = ''

    child.stdout.on('data', (chunk) => {
      stdout += String(chunk)
    })
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk)
    })

    child.on('error', (err) => {
      resolve({
        status: 'Runtime Error',
        passed_count: 0,
        total_count: payload.test_cases?.length ?? 0,
        runtime_ms: 0,
        error: err.message,
        results: [],
      })
    })

    child.on('close', () => {
      try {
        const parsed = JSON.parse(stdout) as RunCodeResult
        resolve(parsed)
      } catch {
        resolve({
          status: 'Runtime Error',
          passed_count: 0,
          total_count: payload.test_cases?.length ?? 0,
          runtime_ms: 0,
          error: (stderr || stdout || 'Code execution failed or timed out').slice(0, 600),
          results: [],
        })
      }
    })

    child.stdin.write(
      JSON.stringify({
        code: payload.code,
        test_code: payload.test_code || '',
        test_cases: payload.test_cases || [],
      }),
    )
    child.stdin.end()
  })
}

const PYTHON_INLINE_HARNESS = `
import io, json, sys, time, traceback, contextlib

payload = json.loads(sys.stdin.read())
code = payload.get("code", "")
test_cases = payload.get("test_cases") or []
test_code = payload.get("test_code") or ""

ns = {}
t0 = time.perf_counter()
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        exec(compile(code, "<solution>", "exec"), ns)
except Exception as exc:
    print(json.dumps({
        "status": "Compile Error" if isinstance(exc, SyntaxError) else "Runtime Error",
        "passed_count": 0,
        "total_count": len(test_cases),
        "runtime_ms": round((time.perf_counter() - t0) * 1000, 2),
        "error": traceback.format_exc().splitlines()[-1],
        "results": [],
    }))
    sys.exit(0)

if not test_cases and not test_code:
    ms = round((time.perf_counter() - t0) * 1000, 2)
    print(json.dumps({
        "status": "Accepted",
        "passed_count": 1,
        "total_count": 1,
        "runtime_ms": ms,
        "error": None,
        "results": [{"test_index": 1, "passed": True, "input": None, "expected": None, "actual": None, "stdout": buf.getvalue(), "error": None, "runtime_ms": ms}],
    }))
    sys.exit(0)

fn = None
if "Solution" in ns and isinstance(ns["Solution"], type):
    inst = ns["Solution"]()
    methods = [m for m in dir(inst) if not m.startswith("_") and callable(getattr(inst, m))]
    if methods:
        fn = getattr(inst, methods[0])
if fn is None:
    for k, v in ns.items():
        if not k.startswith("_") and callable(v) and not isinstance(v, type):
            fn = v
            break

results = []
passed_count = 0
overall = "Accepted"

for idx, tc in enumerate(test_cases):
    inp = tc.get("input")
    exp = tc.get("expected")
    case_buf = io.StringIO()
    ct0 = time.perf_counter()
    actual = None
    err = None
    passed = False
    try:
        if fn is None:
            raise RuntimeError("No callable function or Solution method found.")
        with contextlib.redirect_stdout(case_buf):
            if isinstance(inp, dict):
                actual = fn(**inp)
            elif isinstance(inp, list):
                actual = fn(*inp)
            else:
                actual = fn(inp)
        if isinstance(actual, tuple) and isinstance(exp, list):
            passed = list(actual) == exp
        else:
            passed = actual == exp
        if passed:
            passed_count += 1
        elif overall == "Accepted":
            overall = "Wrong Answer"
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        if overall == "Accepted":
            overall = "Runtime Error"
    cms = round((time.perf_counter() - ct0) * 1000, 2)
    try:
        json.dumps(actual)
        safe_actual = actual
    except Exception:
        safe_actual = repr(actual)
    results.append({
        "test_index": idx + 1,
        "passed": passed,
        "input": inp,
        "expected": exp,
        "actual": safe_actual,
        "stdout": case_buf.getvalue(),
        "error": err,
        "runtime_ms": cms,
    })

print(json.dumps({
    "status": overall,
    "passed_count": passed_count,
    "total_count": len(test_cases),
    "runtime_ms": round(sum(r["runtime_ms"] for r in results), 2),
    "error": next((r["error"] for r in results if r["error"]), None),
    "results": results,
}))
`

function runPythonWorker(payload: RunCodePayload): Promise<RunCodeResult> {
  return new Promise((resolve) => {
    const child = spawn('python3', ['-c', PYTHON_INLINE_HARNESS], {
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 6000,
    })

    let stdout = ''
    let stderr = ''

    child.stdout.on('data', (chunk) => {
      stdout += String(chunk)
    })
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk)
    })

    child.on('error', () => {
      resolve({
        status: 'Runtime Error',
        passed_count: 0,
        total_count: payload.test_cases?.length ?? 0,
        runtime_ms: 0,
        error: 'Python execution is unavailable in this runtime; switch language to TypeScript/JavaScript to execute code.',
        results: [],
      })
    })

    child.on('close', () => {
      try {
        const parsed = JSON.parse(stdout) as RunCodeResult
        resolve(parsed)
      } catch {
        resolve({
          status: 'Runtime Error',
          passed_count: 0,
          total_count: payload.test_cases?.length ?? 0,
          runtime_ms: 0,
          error: (stderr || stdout || 'Python execution failed or timed out').slice(0, 600),
          results: [],
        })
      }
    })

    child.stdin.write(
      JSON.stringify({
        code: payload.code,
        test_code: payload.test_code || '',
        test_cases: payload.test_cases || [],
      }),
    )
    child.stdin.end()
  })
}

export async function executeCode(payload: RunCodePayload): Promise<RunCodeResult> {
  const lang = (payload.language || '').toLowerCase()
  if (lang === 'python' || lang === 'py') {
    return runPythonWorker(payload)
  }
  return runNodeTsWorker(payload)
}
