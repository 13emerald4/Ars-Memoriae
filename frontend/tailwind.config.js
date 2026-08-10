/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: '#0f1117', soft: '#171a23', line: '#252938' },
      },
    },
  },
  plugins: [],
}
