import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import tseslint from 'typescript-eslint'

// What this guards, in order of how much it has already cost:
//   - rules-of-hooks / exhaustive-deps: stale closures and effects that re-run
//     (or fail to) because of a wrong dependency list. Review.tsx shipped both.
//   - no-explicit-any, unused code: kept as warnings so the existing backlog
//     shows up without blocking a commit; new code should not add to it.
// `npm run lint` fails on errors only. Type errors are tsc's job (typecheck).
export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser },
    },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      '@typescript-eslint/no-explicit-any': 'warn',
      // tsc already enforces noUnusedLocals / noUnusedParameters.
      '@typescript-eslint/no-unused-vars': 'off',
      'no-unused-vars': 'off',
      // `cond && doSomething()` and `a ? b() : c()` as statements are used
      // throughout for event handlers.
      '@typescript-eslint/no-unused-expressions': 'off',
      'no-empty': ['warn', { allowEmptyCatch: true }],
      'no-useless-escape': 'warn',
      'prefer-const': 'warn',
    },
  },
  {
    files: ['*.config.{js,ts}'],
    languageOptions: { globals: { ...globals.node } },
  },
)
