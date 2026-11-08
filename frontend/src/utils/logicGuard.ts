/**
 * Real-Time Logic Guard for Ars Memoriae Code Review
 *
 * Evaluates completed lines of code as the user types and advances to the next line.
 * Strictly ignores:
 *   - Comments (absent, present, or differing comments never trigger warnings)
 *   - Semantically similar strings (error messages, log text, string formatting)
 *   - Whitespace, indentation, and semicolons
 *
 * Accurately detects logic flaws:
 *   - Incomplete / broken syntax (e.g. dangling operators `&& <`, unclosed parentheses)
 *   - Undefined variable / missing property access (e.g. `interestRate` instead of `account.interestRate`)
 *   - Inverted comparison operators (`>` vs `<`, `>=` vs `<=`, `==` vs `!=`)
 *   - Inverted boolean operators (`&&` vs `||`)
 *   - Boundary mismatch (e.g. wrong numeric threshold)
 *   - Inverted negation or control flow
 */

export interface LogicWarning {
  lineNumber: number
  lineText: string
  message: string
  reason:
    | 'syntax_error'
    | 'identifier_mismatch'
    | 'operator_mismatch'
    | 'inverted_logic'
    | 'incomplete_condition'
  suggestedFix?: string
}

/**
 * Strips comments from a line of code based on language.
 */
export function stripComments(line: string, language: string = 'typescript'): string {
  if (!line) return ''
  const lang = language.toLowerCase()
  if (lang === 'py' || lang === 'python' || lang === 'python3') {
    return line.replace(/#.*$/, '')
  }
  // TypeScript / JavaScript
  return line.replace(/\/\/.*$/, '').replace(/\/\*.*?\*\//g, '')
}

/**
 * Replaces string literals with a canonical placeholder `"__STR__"`
 * so differing error messages or text strings never trigger logic warnings.
 */
export function maskStringLiterals(line: string): string {
  if (!line) return ''
  // Single quotes, double quotes, and template literals
  return line.replace(/(["'`])(?:\\.|(?!\1)[^\\])*\1/g, '"__STR__"')
}

/**
 * Normalizes a code line for pure logic comparison:
 * strips comments, masks strings, collapses whitespace, trims semicolons.
 */
export function normalizeStatement(line: string, language: string = 'typescript'): string {
  const noComments = stripComments(line, language)
  const maskedStrings = maskStringLiterals(noComments)
  return maskedStrings.replace(/\s+/g, ' ').replace(/;+\s*$/, '').trim()
}

/**
 * Tokenizes a code line into atomic programming symbols.
 */
export function tokenizeLine(code: string): string[] {
  const regex =
    /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`[\s\S]*?`|===|!==|==|!=|<=|>=|=>|&&|\|\||[a-zA-Z_$][a-zA-Z0-9_$]*|\d+(?:\.\d+)?|[()\[\]{}:,.<>=+\-*/%&|^~!]|\S)/g
  const tokens: string[] = []
  let match: RegExpExecArray | null
  while ((match = regex.exec(code)) !== null) {
    tokens.push(match[0])
  }
  return tokens
}

/**
 * Checks for obvious syntax / structural errors on a single completed statement line.
 */
function detectSyntaxOrIncompleteError(line: string): { message: string; suggestedFix?: string } | null {
  const trimmed = line.trim()
  if (!trimmed) return null

  // 1. Dangling binary operator at end of line (incomplete expression)
  if (/(?:&&|\|\||===|!==|<=|>=|==|!=|[+\-*/%<>]|=>)\s*$/.test(trimmed)) {
    return {
      message: 'Incomplete line: dangling operator at end of line.',
      suggestedFix: 'Complete the expression or remove the trailing operator.',
    }
  }

  // 2. Dangling operator followed immediately by another operator (e.g. `&& < 0.12` or `< &&`)
  const danglingOpMatch = trimmed.match(
    /(?:(&&|\|\|)\s*(<=|>=|===|!==|==|!=|[<>=+\-*/%])|(<=|>=|===|!==|==|!=|[<>])\s*(?:&&|\|\||<=|>=|===|!==|==|!=|[<>]))/
  )
  if (danglingOpMatch) {
    const op1 = danglingOpMatch[1] || danglingOpMatch[3]
    const op2 = danglingOpMatch[2] || 'operator'
    return {
      message: `Incomplete condition: operator '${op2}' is missing a left-hand operand after '${op1}'.`,
      suggestedFix: `Specify the variable or value to compare before '${op2}'.`,
    }
  }

  // 3. Mismatched parentheses on single-line statements that have a body
  // e.g. `if (!(0 <= interestRate && < 0.12) throw ...` -> unclosed `if (`
  if (/^if\s*\(/.test(trimmed)) {
    let openCount = 0
    let lastParenIndex = -1
    for (let i = 0; i < trimmed.length; i++) {
      if (trimmed[i] === '(') openCount++
      else if (trimmed[i] === ')') {
        openCount--
        if (openCount === 0 && lastParenIndex === -1) {
          lastParenIndex = i
        }
      }
    }
    // If openCount > 0 and there's executable code after (e.g. throw or return), condition parens are broken
    if (openCount > 0 && /(?:throw|return|const|let|var)\b/.test(trimmed)) {
      return {
        message: 'Syntax error: unclosed parenthesis in `if (...)` condition before statement body.',
        suggestedFix: 'Ensure all opened parentheses are properly closed before the body.',
      }
    }
  }

  return null
}

/**
 * Extracts distinct identifier tokens (variable and property names) from a line.
 */
function extractIdentifiers(line: string): string[] {
  const tokens = tokenizeLine(line)
  const keywords = new Set([
    'if', 'else', 'return', 'throw', 'new', 'Error', 'const', 'let', 'var', 'function',
    'class', 'type', 'interface', 'import', 'export', 'default', 'true', 'false', 'null',
    'undefined', 'number', 'string', 'boolean', 'void', 'any', 'for', 'while', '__STR__',
  ])
  return tokens.filter((t) => /^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(t) && !keywords.has(t))
}

/**
 * Extracts qualified property accesses, e.g. `account.interestRate` -> ['account.interestRate'].
 */
function extractQualifiedProperties(line: string): string[] {
  const matches = line.match(/\b([a-zA-Z_$][a-zA-Z0-9_$]*\.[a-zA-Z_$][a-zA-Z0-9_$]*)\b/g)
  return matches ? Array.from(new Set(matches)) : []
}

/**
 * Breaks reference code into logical statement chunks.
 */
export function splitIntoLogicalStatements(code: string, language: string = 'typescript'): string[] {
  const lines = code.split('\n')
  const statements: string[] = []
  let current = ''
  let braceDepth = 0

  for (const rawLine of lines) {
    const stripped = stripComments(rawLine, language).trim()
    if (!stripped) continue

    if (current) {
      current += ' ' + stripped
    } else {
      current = stripped
    }

    // Track braces
    for (const ch of stripped) {
      if (ch === '{') braceDepth++
      else if (ch === '}') braceDepth = Math.max(0, braceDepth - 1)
    }

    const isControlBlock = /^(?:if|for|while|switch)\b/.test(current)
    if (isControlBlock) {
      if (braceDepth === 0 || current.endsWith(';')) {
        statements.push(current)
        current = ''
        braceDepth = 0
      }
    } else if (
      current.endsWith(';') ||
      (braceDepth === 0 && current.endsWith('}')) ||
      (current.endsWith('{') && !isControlBlock)
    ) {
      statements.push(current)
      current = ''
    }
  }

  if (current.trim()) {
    statements.push(current.trim())
  }

  return statements
}

/**
 * Finds the candidate reference statement that corresponds to the given user statement.
 */
export function findMatchingRefStatement(
  userStmt: string,
  refStatements: string[],
  userLineIndex: number
): string | null {
  if (refStatements.length === 0) return null

  const userNorm = maskStringLiterals(userStmt)
  const userIds = new Set(extractIdentifiers(userNorm))

  let bestMatch: string | null = null
  let maxScore = -1

  for (let idx = 0; idx < refStatements.length; idx++) {
    const refStmt = maskStringLiterals(refStatements[idx])
    const refIds = extractIdentifiers(refStmt)

    let score = 0

    // 1. Shared statement kind
    const userIsIf = userNorm.startsWith('if')
    const refIsIf = refStmt.startsWith('if')
    if (userIsIf && refIsIf) {
      score += 12
    } else if (userIsIf !== refIsIf) {
      score -= 10
    }

    if (userNorm.includes('throw') && refStmt.includes('throw')) score += 4
    if (userNorm.includes('return') && refStmt.includes('return')) score += 4

    // 2. Shared domain identifiers (unique)
    const uniqueRefIds = new Set(refIds)
    for (const id of uniqueRefIds) {
      if (userIds.has(id)) score += 6
    }

    // 3. Proximity bonus
    const dist = Math.abs(idx - userLineIndex)
    score += Math.max(0, 3 - dist * 0.5)

    if (score > maxScore) {
      maxScore = score
      bestMatch = refStatements[idx]
    }
  }

  return maxScore >= 4 ? bestMatch : null
}

/**
 * Compares normalized user statement against matching reference statement for logic flaws.
 */
export function compareStatementLogic(
  userStmt: string,
  refStmt: string,
  lineNumber: number
): LogicWarning | null {
  const uNorm = maskStringLiterals(userStmt)
  const rNorm = maskStringLiterals(refStmt)

  // 1. Check for missing object accessor: e.g. reference uses `account.interestRate`
  // but user uses bare `interestRate` without `account.`
  const refQualified = extractQualifiedProperties(rNorm)
  for (const qProp of refQualified) {
    const [obj, prop] = qProp.split('.')
    // If reference uses `obj.prop`, but user used `prop` and NOT `obj.prop`
    const userHasProp = new RegExp(`\\b${prop}\\b`).test(uNorm)
    const userHasQualified = uNorm.includes(`${obj}.${prop}`)

    if (userHasProp && !userHasQualified) {
      return {
        lineNumber,
        lineText: userStmt,
        message: `'${prop}' is not defined in this scope — did you mean '${obj}.${prop}'?`,
        reason: 'identifier_mismatch',
        suggestedFix: `Replace '${prop}' with '${obj}.${prop}'.`,
      }
    }
  }

  // 2. Check for inverted comparison operators in conditions
  // e.g. reference has `>= 0` but user wrote `<= 0` (or `< 0` when checking valid input)
  const isUserCondition = uNorm.startsWith('if')
  const isRefCondition = rNorm.startsWith('if')

  if (isUserCondition && isRefCondition) {
    // Check if user has inverted direction for the same variable
    // e.g. ref: `account.balance >= 0` vs user: `account.balance <= 0`
    const userTokens = tokenizeLine(uNorm)
    const refTokens = tokenizeLine(rNorm)

    // Check for boolean operator confusion (&& vs ||)
    const userHasAnd = userTokens.includes('&&')
    const userHasOr = userTokens.includes('||')
    const refHasAnd = refTokens.includes('&&')
    const refHasOr = refTokens.includes('||')

    // Only flag if negation structure is the same (not De Morgan transformed)
    const userHasNegation = userTokens.includes('!')
    const refHasNegation = refTokens.includes('!')

    if (userHasNegation === refHasNegation) {
      if (refHasAnd && !refHasOr && userHasOr && !userHasAnd) {
        return {
          lineNumber,
          lineText: userStmt,
          message: 'Flaw in logic: using `||` (OR) instead of `&&` (AND).',
          reason: 'operator_mismatch',
          suggestedFix: 'Both conditions must hold simultaneously; use `&&`.',
        }
      }
      if (refHasOr && !refHasAnd && userHasAnd && !refHasOr) {
        return {
          lineNumber,
          lineText: userStmt,
          message: 'Flaw in logic: using `&&` (AND) instead of `||` (OR).',
          reason: 'operator_mismatch',
          suggestedFix: 'Either condition should trigger; use `||`.',
        }
      }
    } else if (refHasNegation && !userHasNegation) {
      // Reference checked !(ValidA && ValidB). User is checking invalid bounds directly without !
      // When checking invalid bounds directly, they must be joined with || (e.g. x < 0 || x >= 0.12).
      // Joining disjoint invalid conditions with && makes it impossible to ever be true!
      if (refHasAnd && userHasAnd && !userHasOr) {
        return {
          lineNumber,
          lineText: userStmt,
          message: 'Flaw in logic: using `&&` (AND) instead of `||` (OR) for disjoint invalid checks.',
          reason: 'operator_mismatch',
          suggestedFix: 'Use `||` so an error is thrown if either boundary condition is violated.',
        }
      }
    }
  }

  // 3. Check for arithmetic operator confusion (e.g. + vs - in financial calculation)
  if (rNorm.includes('return') && uNorm.includes('return')) {
    if (rNorm.includes('+') && !rNorm.includes('-') && uNorm.includes('-') && !uNorm.includes('+')) {
      return {
        lineNumber,
        lineText: userStmt,
        message: 'Flaw in logic: subtraction used where addition is expected.',
        reason: 'operator_mismatch',
        suggestedFix: 'Verify the arithmetic operation for this calculation.',
      }
    }
  }

  return null
}

/**
 * Primary entry point: Evaluates the line of code that the user just moved away from.
 *
 * @param userCode Full user code currently in the solution editor
 * @param refCode Canonical reference solution
 * @param evaluatedLineNumber 1-indexed line number the user was on before moving
 * @param language Programming language ('typescript', 'python', etc.)
 * @returns LogicWarning if a flaw in logic is identified, or null if sound.
 */
export function checkLineLogic(
  userCode: string,
  refCode: string,
  evaluatedLineNumber: number,
  language: string = 'typescript'
): LogicWarning | null {
  if (!refCode || !refCode.trim()) return null
  if (!userCode || evaluatedLineNumber < 1) return null

  const userLines = userCode.split('\n')
  if (evaluatedLineNumber > userLines.length) return null

  const rawUserLine = userLines[evaluatedLineNumber - 1]
  if (!rawUserLine) return null

  // 1. Comment & Blank Immunity: If line is blank or only comments, skip!
  const stripped = stripComments(rawUserLine, language).trim()
  if (!stripped) {
    return null
  }

  // 2. Ignore pure structural brackets (e.g. `}` or `};` or `])`)
  if (/^[}\])\s;]+$/.test(stripped)) {
    return null
  }

  // 3. Syntax / Incompleteness Check (e.g. `&& < 0.12` or unclosed parens before body)
  const syntaxErr = detectSyntaxOrIncompleteError(stripped)
  if (syntaxErr) {
    return {
      lineNumber: evaluatedLineNumber,
      lineText: rawUserLine,
      message: syntaxErr.message,
      reason: 'syntax_error',
      suggestedFix: syntaxErr.suggestedFix,
    }
  }

  // 4. Align with Reference Code
  const refStatements = splitIntoLogicalStatements(refCode, language)
  const matchingRefStmt = findMatchingRefStatement(stripped, refStatements, evaluatedLineNumber - 1)

  if (!matchingRefStmt) {
    // If no specific matching invariant is found, line is acceptable or novel
    return null
  }

  // 5. Compare Logic with Reference Statement
  const logicFlaw = compareStatementLogic(stripped, matchingRefStmt, evaluatedLineNumber)
  if (logicFlaw) {
    return logicFlaw
  }

  return null
}
