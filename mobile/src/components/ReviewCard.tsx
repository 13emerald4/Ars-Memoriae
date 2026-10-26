import React, { useState } from 'react'
import {
  ActivityIndicator,
  Keyboard,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  TouchableWithoutFeedback,
  View,
} from 'react-native'
import type { Card, Grade, SubmitAnswerResponse } from '../types'

interface ReviewCardProps {
  card: Card
  onConfirm: (grade: Grade, typedAnswer: string, latencyMs: number) => Promise<void>
  onSubmitAnswer: (cardId: string, answer: string, latencyMs: number) => Promise<SubmitAnswerResponse>
}

export function ReviewCard({ card, onConfirm, onSubmitAnswer }: ReviewCardProps) {
  const [typedAnswer, setTypedAnswer] = useState('')
  const [startTime] = useState(Date.now())
  const [evaluating, setEvaluating] = useState(false)
  const [evaluation, setEvaluation] = useState<SubmitAnswerResponse | null>(null)
  const [submittingGrade, setSubmittingGrade] = useState<Grade | null>(null)

  const handleSubmit = async () => {
    if (!typedAnswer.trim() || evaluating) return
    Keyboard.dismiss()
    setEvaluating(true)
    const latencyMs = Date.now() - startTime
    try {
      const result = await onSubmitAnswer(card.id, typedAnswer, latencyMs)
      setEvaluation(result)
    } catch {
      // Fallback if offline or grading server is down: reveal answer for self-assessment
      setEvaluation({
        suggested_grade: 'good',
        confidence: 0,
        reasoning: 'Grading service unreachable. Self-grade using reference answer.',
        reference_answer: card.back,
        heuristic_overlap: 0,
        needs_confirmation: true,
      })
    } finally {
      setEvaluating(false)
    }
  }

  const handleGradeConfirm = async (grade: Grade) => {
    setSubmittingGrade(grade)
    const latencyMs = Date.now() - startTime
    try {
      await onConfirm(grade, typedAnswer, latencyMs)
    } finally {
      setSubmittingGrade(null)
    }
  }

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
      <View style={styles.cardContainer}>
        {/* Card Header & Deck Name */}
        <View style={styles.cardHeader}>
          <Text style={styles.deckBadge}>{card.deck_name || 'Active Deck'}</Text>
          <Text style={styles.stateBadge}>{card.state.toUpperCase()}</Text>
        </View>

        {/* Card Front Prompt */}
        <View style={styles.promptBox}>
          <Text style={styles.promptLabel}>QUESTION</Text>
          <Text style={styles.promptText}>{card.front}</Text>
        </View>

        {/* Typed Answer Input */}
        {!evaluation ? (
          <View style={styles.inputSection}>
            <Text style={styles.inputLabel}>TYPE YOUR ANSWER (ACTIVE RECALL)</Text>
            <TextInput
              style={styles.textInput}
              multiline
              autoFocus
              placeholder="Type your response here..."
              placeholderTextColor="#64748b"
              value={typedAnswer}
              onChangeText={setTypedAnswer}
            />

            <TouchableOpacity
              style={[styles.submitButton, (!typedAnswer.trim() || evaluating) && styles.disabledButton]}
              disabled={!typedAnswer.trim() || evaluating}
              onPress={handleSubmit}
            >
              {evaluating ? (
                <ActivityIndicator color="#ffffff" size="small" />
              ) : (
                <Text style={styles.submitButtonText}>Submit for AI Evaluation</Text>
              )}
            </TouchableOpacity>
          </View>
        ) : (
          /* Evaluation & Reference Answer */
          <View style={styles.evalSection}>
            <View style={styles.evalHeader}>
              <View style={[styles.suggestedBadge, getGradeBadgeStyle(evaluation.suggested_grade)]}>
                <Text style={styles.suggestedBadgeText}>
                  AI Suggested: {evaluation.suggested_grade.toUpperCase()}
                </Text>
              </View>
              {evaluation.heuristic_overlap > 0 && (
                <Text style={styles.overlapText}>
                  {Math.round(evaluation.heuristic_overlap * 100)}% match
                </Text>
              )}
            </View>

            {evaluation.reasoning ? (
              <View style={styles.reasoningBox}>
                <Text style={styles.reasoningText}>{evaluation.reasoning}</Text>
              </View>
            ) : null}

            <View style={styles.referenceBox}>
              <Text style={styles.referenceLabel}>REFERENCE ANSWER</Text>
              <Text style={styles.referenceText}>{evaluation.reference_answer || card.back}</Text>
            </View>

            {/* FSRS Confirmation Buttons */}
            <Text style={styles.confirmPrompt}>Confirm your rating to schedule:</Text>
            <View style={styles.buttonRow}>
              {(['again', 'hard', 'good', 'easy'] as Grade[]).map((g) => (
                <TouchableOpacity
                  key={g}
                  style={[
                    styles.gradeButton,
                    getGradeButtonStyle(g),
                    submittingGrade === g && styles.submittingGradeButton,
                  ]}
                  disabled={submittingGrade !== null}
                  onPress={() => handleGradeConfirm(g)}
                >
                  <Text style={styles.gradeButtonText}>
                    {submittingGrade === g ? '...' : g.toUpperCase()}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
      </View>
    </TouchableWithoutFeedback>
  )
}

function getGradeBadgeStyle(grade: Grade) {
  switch (grade) {
    case 'again':
      return { backgroundColor: '#ef4444' }
    case 'hard':
      return { backgroundColor: '#f97316' }
    case 'good':
      return { backgroundColor: '#0ea5e9' }
    case 'easy':
      return { backgroundColor: '#10b981' }
  }
}

function getGradeButtonStyle(grade: Grade) {
  switch (grade) {
    case 'again':
      return { backgroundColor: '#ef4444' }
    case 'hard':
      return { backgroundColor: '#f97316' }
    case 'good':
      return { backgroundColor: '#0284c7' }
    case 'easy':
      return { backgroundColor: '#059669' }
  }
}

const styles = StyleSheet.create({
  cardContainer: {
    backgroundColor: '#1e293b',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155',
    marginVertical: 10,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 4,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  deckBadge: {
    color: '#38bdf8',
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  stateBadge: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '600',
  },
  promptBox: {
    marginBottom: 20,
  },
  promptLabel: {
    color: '#64748b',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 6,
  },
  promptText: {
    color: '#f8fafc',
    fontSize: 18,
    lineHeight: 26,
    fontWeight: '600',
  },
  inputSection: {
    marginTop: 10,
  },
  inputLabel: {
    color: '#94a3b8',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  textInput: {
    backgroundColor: '#0f172a',
    borderColor: '#334155',
    borderWidth: 1,
    borderRadius: 12,
    color: '#f8fafc',
    padding: 14,
    fontSize: 15,
    minHeight: 110,
    textAlignVertical: 'top',
  },
  submitButton: {
    backgroundColor: '#38bdf8',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 16,
  },
  disabledButton: {
    backgroundColor: '#475569',
    opacity: 0.6,
  },
  submitButtonText: {
    color: '#0f172a',
    fontSize: 15,
    fontWeight: '700',
  },
  evalSection: {
    marginTop: 10,
  },
  evalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  suggestedBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  suggestedBadgeText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '800',
  },
  overlapText: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '600',
  },
  reasoningBox: {
    backgroundColor: '#0f172a',
    borderRadius: 8,
    padding: 12,
    marginBottom: 14,
    borderLeftWidth: 3,
    borderLeftColor: '#38bdf8',
  },
  reasoningText: {
    color: '#cbd5e1',
    fontSize: 13,
    lineHeight: 18,
  },
  referenceBox: {
    backgroundColor: '#090d16',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  referenceLabel: {
    color: '#64748b',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  referenceText: {
    color: '#e2e8f0',
    fontSize: 14,
    lineHeight: 20,
  },
  confirmPrompt: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '600',
    marginBottom: 10,
    textAlign: 'center',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
  },
  gradeButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  submittingGradeButton: {
    opacity: 0.5,
  },
  gradeButtonText: {
    color: '#ffffff',
    fontWeight: '800',
    fontSize: 12,
  },
})
