/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Verdana', 'Geneva', 'Tahoma', 'sans-serif'],
      },
      colors: {
        ink: {
          DEFAULT: 'var(--theme-bg-canvas, #0f1117)',
          soft: 'var(--theme-bg-card, #171a23)',
          line: 'var(--theme-border, #252938)',
        },
      },
    },
  },
  plugins: [],
}
