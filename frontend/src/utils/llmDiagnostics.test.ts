import { describe, it, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import {
  _resetLlmTracesForTest,
  buildDiagnosticReport,
  describeGradingStage,
  diagnoseLlmTrace,
  finishLlmTrace,
  getLlmTraceById,
  getLlmTraceSnapshot,
  isEmptyOllamaError,
  isThinkingModel,
  startLlmTrace,
} from './llmDiagnostics'

describe('llmDiagnostics', () => {
  beforeEach(() => {
    _resetLlmTracesForTest()
  })

  it('detects empty Ollama generation failed errors', () => {
    assert.equal(isEmptyOllamaError('Ollama generation failed:'), true)
    assert.equal(isEmptyOllamaError('Ollama generation failed:   '), true)
    assert.equal(isEmptyOllamaError('Ollama generation failed: connection refused'), false)
  })

  it('identifies Qwen 3.5 and reasoning models with thinking overhead', () => {
    assert.equal(isThinkingModel('qwen3.5:4b'), true)
    assert.equal(isThinkingModel('qwen3.5:9b'), true)
    assert.equal(isThinkingModel('qwen2.5-coder:7b'), false)
    assert.equal(isThinkingModel(null), false)
  })

  it('diagnoses empty Ollama failure on qwen3.5:4b with thinking-token and timeout guidance', () => {
    const diagnosis = diagnoseLlmTrace({
      model: 'qwen3.5:4b',
      durationMs: 32_400,
      status: 'error',
      httpStatus: 500,
      errorMessage: 'Ollama generation failed:',
      rawDetail: 'Ollama generation failed:',
      degradedReason: null,
      chromeContext: {
        visibilityState: 'visible',
        online: true,
        inFlightCount: 1,
        hardwareConcurrency: 8,
        deviceMemoryGb: 8,
        jsHeapUsedMb: 90,
        jsHeapLimitMb: 2048,
        browserLabel: 'Google Chrome',
      },
    })

    assert.equal(diagnosis.code, 'empty_ollama_error')
    assert.equal(diagnosis.severity, 'error')
    assert.match(diagnosis.summary, /httpx\.ReadTimeout/i)
    assert.ok(diagnosis.likelyCauses.some((c) => /thinking tokens/i.test(c)))
    assert.ok(diagnosis.suggestedFixes.some((f) => /qwen2\.5-coder:7b|think: false/i.test(f)))
  })

  it('diagnoses concurrent LLM requests as queue contention when slow', () => {
    const diagnosis = diagnoseLlmTrace({
      model: 'qwen2.5-coder:7b',
      durationMs: 14_000,
      status: 'slow',
      httpStatus: 200,
      errorMessage: null,
      rawDetail: null,
      degradedReason: null,
      chromeContext: {
        visibilityState: 'visible',
        online: true,
        inFlightCount: 3,
        hardwareConcurrency: 8,
        deviceMemoryGb: 8,
        jsHeapUsedMb: null,
        jsHeapLimitMb: null,
        browserLabel: 'Google Chrome',
      },
    })

    assert.equal(diagnosis.code, 'concurrent_queue_contention')
    assert.equal(diagnosis.severity, 'warn')
  })

  it('tracks active traces, computes duration, and surfaces lastFailure in snapshot', () => {
    const id = startLlmTrace({
      operation: 'Grade Answer',
      endpoint: '/api/review/card-1/answer',
      model: 'qwen3.5:4b',
    })

    assert.equal(getLlmTraceSnapshot().activeCount, 1)
    assert.equal(getLlmTraceById(id)?.status, 'pending')

    const finished = finishLlmTrace(id, {
      status: 'error',
      httpStatus: 502,
      errorMessage: 'Ollama generation failed:',
      rawDetail: 'Ollama generation failed:',
    })

    assert.ok(finished)
    assert.equal(finished.status, 'error')
    assert.equal(finished.diagnosis?.code, 'empty_ollama_error')
    assert.equal(getLlmTraceSnapshot().activeCount, 0)
    assert.equal(getLlmTraceSnapshot().lastFailure?.id, id)

    const report = JSON.parse(buildDiagnosticReport(getLlmTraceSnapshot(), null, 'qwen3.5:4b'))
    assert.equal(report.active_model, 'qwen3.5:4b')
    assert.equal(report.recent_client_traces.length, 1)
    assert.equal(report.recent_client_traces[0].diagnosis_code, 'empty_ollama_error')
  })

  it('describes live grading stages across latency thresholds', () => {
    assert.equal(describeGradingStage(800, 'qwen3.5:4b').phase, 'sending')
    assert.equal(describeGradingStage(4_000, 'qwen3.5:4b').phase, 'generating')
    assert.equal(describeGradingStage(12_000, 'qwen3.5:4b').phase, 'slow')
    assert.equal(describeGradingStage(26_000, 'qwen3.5:4b').phase, 'stalled')
  })
})
