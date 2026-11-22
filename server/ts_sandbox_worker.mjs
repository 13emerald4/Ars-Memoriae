import fs from 'node:fs'
import vm from 'node:vm'
import { performance } from 'node:perf_hooks'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)

function loadTypeScript() {
  const candidates = [
    path.resolve(__dirname, '..', 'node_modules', 'typescript'),
    path.resolve(__dirname, '..', 'frontend', 'node_modules', 'typescript'),
    'typescript',
  ]
  for (const candidate of candidates) {
    try {
      return require(candidate)
    } catch {
      // try next candidate
    }
  }
  return null
}

function deepEqual(a, b) {
  if (Object.is(a, b)) return true
  if (typeof a !== typeof b || a === null || b === null) return false
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false
    for (let i = 0; i < a.length; i++) {
      if (!deepEqual(a[i], b[i])) return false
    }
    return true
  }
  if (Array.isArray(a) !== Array.isArray(b)) return false
  if (typeof a === 'object' && typeof b === 'object') {
    const keysA = Object.keys(a)
    const keysB = Object.keys(b)
    if (keysA.length !== keysB.length) return false
    for (const key of keysA) {
      if (!Object.prototype.hasOwnProperty.call(b, key)) return false
      if (!deepEqual(a[key], b[key])) return false
    }
    return true
  }
  return false
}

function safeClone(val) {
  if (val === undefined) return null
  try {
    return JSON.parse(JSON.stringify(val))
  } catch {
    return String(val)
  }
}

function formatArgs(args) {
  return args
    .map((a) => {
      if (typeof a === 'string') return a
      try {
        return JSON.stringify(a)
      } catch {
        return String(a)
      }
    })
    .join(' ')
}

function makeExpect(actual) {
  function check(pass, msg, inverted) {
    const ok = inverted ? !pass : pass
    if (!ok) {
      throw new Error(msg)
    }
  }
  function buildMatchers(inverted) {
    return {
      toBe(expected) {
        check(
          Object.is(actual, expected),
          `Expected ${JSON.stringify(actual)} ${inverted ? 'not ' : ''}to be ${JSON.stringify(expected)}`,
          inverted,
        )
      },
      toEqual(expected) {
        check(
          deepEqual(actual, expected),
          `Expected ${JSON.stringify(actual)} ${inverted ? 'not ' : ''}to equal ${JSON.stringify(expected)}`,
          inverted,
        )
      },
      toStrictEqual(expected) {
        check(
          deepEqual(actual, expected),
          `Expected ${JSON.stringify(actual)} ${inverted ? 'not ' : ''}to strictly equal ${JSON.stringify(expected)}`,
          inverted,
        )
      },
      toBeTruthy() {
        check(Boolean(actual), `Expected ${JSON.stringify(actual)} to be truthy`, inverted)
      },
      toBeFalsy() {
        check(!actual, `Expected ${JSON.stringify(actual)} to be falsy`, inverted)
      },
      toBeNull() {
        check(actual === null, `Expected ${JSON.stringify(actual)} to be null`, inverted)
      },
      toBeUndefined() {
        check(actual === undefined, `Expected ${JSON.stringify(actual)} to be undefined`, inverted)
      },
      toBeDefined() {
        check(actual !== undefined, `Expected value to be defined`, inverted)
      },
      toBeGreaterThan(n) {
        check(actual > n, `Expected ${actual} to be greater than ${n}`, inverted)
      },
      toBeGreaterThanOrEqual(n) {
        check(actual >= n, `Expected ${actual} to be >= ${n}`, inverted)
      },
      toBeLessThan(n) {
        check(actual < n, `Expected ${actual} to be less than ${n}`, inverted)
      },
      toBeLessThanOrEqual(n) {
        check(actual <= n, `Expected ${actual} to be <= ${n}`, inverted)
      },
      toBeCloseTo(expected, digits = 2) {
        const diff = Math.abs(actual - expected)
        const tol = Math.pow(10, -digits) / 2
        check(diff < tol, `Expected ${actual} to be close to ${expected}`, inverted)
      },
      toHaveLength(len) {
        const actualLen = actual?.length
        check(actualLen === len, `Expected length ${len}, got ${actualLen}`, inverted)
      },
      toContain(item) {
        const has = Array.isArray(actual)
          ? actual.some((x) => deepEqual(x, item))
          : typeof actual === 'string'
            ? actual.includes(String(item))
            : false
        check(has, `Expected ${JSON.stringify(actual)} to contain ${JSON.stringify(item)}`, inverted)
      },
      toThrow(expectedMsg) {
        let threw = false
        let errMsg = ''
        try {
          if (typeof actual === 'function') actual()
        } catch (err) {
          threw = true
          errMsg = err instanceof Error ? err.message : String(err)
        }
        let pass = threw
        if (threw && expectedMsg !== undefined) {
          if (expectedMsg instanceof RegExp) pass = expectedMsg.test(errMsg)
          else pass = errMsg.includes(String(expectedMsg))
        }
        check(pass, `Expected function ${inverted ? 'not ' : ''}to throw`, inverted)
      },
    }
  }
  const matchers = buildMatchers(false)
  matchers.not = buildMatchers(true)
  return matchers
}

function transpileTs(ts, source, filename = 'solution.ts') {
  if (!ts) return { code: source, error: null }
  const result = ts.transpileModule(source, {
    fileName: filename,
    reportDiagnostics: true,
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
      allowJs: true,
      strict: false,
    },
  })
  const syntaxDiag = (result.diagnostics || []).find(
    (d) => d.category === ts.DiagnosticCategory.Error,
  )
  if (syntaxDiag) {
    const msg = ts.flattenDiagnosticMessageText(syntaxDiag.messageText, '\n')
    return { code: '', error: `Syntax/TypeScript Error: ${msg}` }
  }
  return { code: result.outputText, error: null }
}

function findEntryFunction(sandbox, exportsObj, preExistingKeys) {
  // 1. Explicit exports
  if (typeof exportsObj === 'function') return exportsObj
  if (exportsObj && typeof exportsObj === 'object') {
    if (typeof exportsObj.default === 'function') return exportsObj.default
    for (const [k, v] of Object.entries(exportsObj)) {
      if (k === '__esModule') continue
      if (typeof v === 'function') {
        if (k === 'Solution' && v.prototype) {
          const inst = new v()
          const methodName = Object.getOwnPropertyNames(v.prototype).find(
            (m) => m !== 'constructor' && typeof inst[m] === 'function',
          )
          if (methodName) return (...args) => inst[methodName](...args)
        }
        return v
      }
    }
  }

  // 2. Solution class on sandbox
  if (typeof sandbox.Solution === 'function' && sandbox.Solution.prototype) {
    const inst = new sandbox.Solution()
    const methodName = Object.getOwnPropertyNames(sandbox.Solution.prototype).find(
      (m) => m !== 'constructor' && typeof inst[m] === 'function',
    )
    if (methodName) return (...args) => inst[methodName](...args)
  }

  // 3. Newly declared top-level function on sandbox
  for (const key of Object.keys(sandbox)) {
    if (preExistingKeys.has(key)) continue
    if (typeof sandbox[key] === 'function') {
      return sandbox[key]
    }
  }

  return null
}

function main() {
  const raw = fs.readFileSync(0, 'utf8')
  const payload = raw.trim() ? JSON.parse(raw) : {}
  const code = String(payload.code || '')
  const testCode = String(payload.test_code || '')
  const testCases = Array.isArray(payload.test_cases) ? payload.test_cases : []

  const ts = loadTypeScript()
  const t0 = performance.now()

  // Extract top-level declared function/const/class names so CommonJS transpiled declarations are also attached to globalThis
  const transpiled = transpileTs(ts, code, 'solution.ts')
  if (transpiled.error) {
    process.stdout.write(
      JSON.stringify({
        status: 'Compile Error',
        passed_count: 0,
        total_count: testCases.length,
        runtime_ms: Number((performance.now() - t0).toFixed(2)),
        error: transpiled.error,
        results: [],
      }),
    )
    return
  }

  const stdoutLines = []
  let activeBuffer = stdoutLines

  const moduleObj = { exports: {} }
  const sandbox = {
    console: {
      log: (...args) => activeBuffer.push(formatArgs(args)),
      info: (...args) => activeBuffer.push(formatArgs(args)),
      warn: (...args) => activeBuffer.push(formatArgs(args)),
      error: (...args) => activeBuffer.push(formatArgs(args)),
    },
    exports: moduleObj.exports,
    module: moduleObj,
    Map,
    Set,
    WeakMap,
    WeakSet,
    Math,
    JSON,
    Array,
    Object,
    String,
    Number,
    Boolean,
    RegExp,
    Date,
    Error,
    TypeError,
    RangeError,
    SyntaxError,
    Promise,
    Symbol,
    BigInt,
    Int32Array,
    Uint32Array,
    Float64Array,
    parseInt,
    parseFloat,
    isNaN,
    isFinite,
    structuredClone,
  }
  const preExistingKeys = new Set(Object.keys(sandbox))
  const context = vm.createContext(sandbox)

  try {
    // Strip "use strict"; and Object.defineProperty(exports, "__esModule", ...) not needed if top-level var/function
    const script = new vm.Script(transpiled.code, { filename: 'solution.js' })
    script.runInContext(context, { timeout: 3500 })
  } catch (err) {
    process.stdout.write(
      JSON.stringify({
        status: 'Runtime Error',
        passed_count: 0,
        total_count: testCases.length,
        runtime_ms: Number((performance.now() - t0).toFixed(2)),
        error: err instanceof Error ? `${err.name}: ${err.message}` : String(err),
        results: [],
      }),
    )
    return
  }

  // Also run student test_code if provided
  const studentTests = []
  let studentPassed = 0
  if (testCode.trim()) {
    const tTest = transpileTs(ts, testCode, 'tests.ts')
    if (tTest.error) {
      studentTests.push({
        test_name: 'Test Compilation',
        passed: false,
        error: tTest.error,
        runtime_ms: 0,
      })
    } else {
      const suitePrefix = []
      const collectedTests = []
      sandbox.describe = (name, fn) => {
        suitePrefix.push(String(name))
        try {
          fn()
        } finally {
          suitePrefix.pop()
        }
      }
      sandbox.it = (name, fn) => {
        collectedTests.push({
          name: [...suitePrefix, String(name)].join(' > '),
          fn,
        })
      }
      sandbox.test = sandbox.it
      sandbox.expect = makeExpect

      // Expose exported symbols directly into sandbox so tests can call them without import
      if (moduleObj.exports && typeof moduleObj.exports === 'object') {
        for (const [k, v] of Object.entries(moduleObj.exports)) {
          if (k !== '__esModule' && !(k in sandbox)) {
            sandbox[k] = v
          }
        }
      }

      try {
        const testScript = new vm.Script(tTest.code, { filename: 'tests.js' })
        testScript.runInContext(context, { timeout: 3500 })
        for (const t of collectedTests) {
          const st0 = performance.now()
          try {
            t.fn()
            studentPassed++
            studentTests.push({
              test_name: t.name,
              passed: true,
              error: null,
              runtime_ms: Number((performance.now() - st0).toFixed(2)),
            })
          } catch (err) {
            studentTests.push({
              test_name: t.name,
              passed: false,
              error: err instanceof Error ? err.message : String(err),
              runtime_ms: Number((performance.now() - st0).toFixed(2)),
            })
          }
        }
      } catch (err) {
        studentTests.push({
          test_name: 'Test Runner',
          passed: false,
          error: err instanceof Error ? err.message : String(err),
          runtime_ms: 0,
        })
      }
    }
  }

  // Free-run mode (no test cases and no student tests)
  if (testCases.length === 0) {
    const ms = Number((performance.now() - t0).toFixed(2))
    const allStudentPassed = studentTests.length === 0 || studentPassed === studentTests.length
    process.stdout.write(
      JSON.stringify({
        status: allStudentPassed ? 'Accepted' : 'Wrong Answer',
        passed_count: studentTests.length > 0 ? studentPassed : 1,
        total_count: studentTests.length > 0 ? studentTests.length : 1,
        runtime_ms: ms,
        error: studentTests.find((t) => !t.passed)?.error ?? null,
        results:
          studentTests.length > 0
            ? studentTests.map((t, idx) => ({
                test_index: idx + 1,
                passed: t.passed,
                input: t.test_name,
                expected: 'pass',
                actual: t.passed ? 'pass' : 'fail',
                stdout: idx === 0 ? stdoutLines.join('\n') : '',
                error: t.error,
                runtime_ms: t.runtime_ms,
              }))
            : [
                {
                  test_index: 1,
                  passed: true,
                  input: null,
                  expected: null,
                  actual: null,
                  stdout: stdoutLines.join('\n'),
                  error: null,
                  runtime_ms: ms,
                },
              ],
        student_tests: studentTests.length > 0 ? studentTests : undefined,
        student_passed_count: studentTests.length > 0 ? studentPassed : undefined,
        student_total_count: studentTests.length > 0 ? studentTests.length : undefined,
      }),
    )
    return
  }

  const fn = findEntryFunction(sandbox, moduleObj.exports, preExistingKeys)
  const results = []
  let passedCount = 0
  let overall = 'Accepted'

  for (let i = 0; i < testCases.length; i++) {
    const tc = testCases[i] || {}
    const inp = tc.input
    const exp = tc.expected
    const caseStdout = []
    activeBuffer = caseStdout
    const ct0 = performance.now()
    let actual = null
    let err = null
    let passed = false

    try {
      if (typeof fn !== 'function') {
        throw new Error('No callable function or Solution method found.')
      }
      if (inp && typeof inp === 'object' && !Array.isArray(inp)) {
        const vals = Object.values(inp)
        actual = fn(...vals)
      } else if (Array.isArray(inp)) {
        actual = fn(...inp)
      } else {
        actual = fn(inp)
      }
      passed = deepEqual(actual, exp)
      if (passed) {
        passedCount++
      } else if (overall === 'Accepted') {
        overall = 'Wrong Answer'
      }
    } catch (e) {
      err = e instanceof Error ? `${e.name}: ${e.message}` : String(e)
      if (overall === 'Accepted') overall = 'Runtime Error'
    }

    const cms = Number((performance.now() - ct0).toFixed(2))
    results.push({
      test_index: i + 1,
      passed,
      input: safeClone(inp),
      expected: safeClone(exp),
      actual: safeClone(actual),
      stdout: caseStdout.join('\n'),
      error: err,
      runtime_ms: cms,
    })
  }

  process.stdout.write(
    JSON.stringify({
      status: overall,
      passed_count: passedCount,
      total_count: testCases.length,
      runtime_ms: Number(results.reduce((acc, r) => acc + r.runtime_ms, 0).toFixed(2)),
      error: results.find((r) => r.error)?.error ?? null,
      results,
      student_tests: studentTests.length > 0 ? studentTests : undefined,
      student_passed_count: studentTests.length > 0 ? studentPassed : undefined,
      student_total_count: studentTests.length > 0 ? studentTests.length : undefined,
    }),
  )
}

main()
