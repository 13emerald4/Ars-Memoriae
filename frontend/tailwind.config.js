/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // The app is dark-only and index.html carries class="dark". Without this,
  // Tailwind's default ("media") made every `dark:` variant follow the
  // operating system instead, so light-mode OS users got white panels.
  darkMode: 'class',
  theme: {
    extend: {
      spacing: {
        // Hairline padding used by keyboard hints and count badges.
        0.2: '0.05rem',
        88: '22rem',
      },
      fontFamily: {
        sans: ['Verdana', 'Geneva', 'Tahoma', 'sans-serif'],
      },
      colors: {
        // Channel triplets, not hex: Tailwind can only apply an opacity
        // modifier (`bg-ink/90`, `border-ink-line/60`) to a colour it can
        // decompose. Defined as plain `var(--hex)`, every one of those ~230
        // classes compiled to nothing, so borders fell back to the browser
        // default (near white) and translucent panels had no background.
        ink: {
          DEFAULT: 'rgb(var(--theme-bg-canvas-rgb, 15 17 23) / <alpha-value>)',
          soft: 'rgb(var(--theme-bg-card-rgb, 23 26 35) / <alpha-value>)',
          line: 'rgb(var(--theme-border-rgb, 37 41 56) / <alpha-value>)',
        },
      },
      boxShadow: {
        xs: '0 1px 2px 0 rgb(0 0 0 / 0.25)',
      },
      zIndex: {
        60: '60',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },
      animation: {
        'fade-in': 'fade-in 180ms ease-out both',
        fadeIn: 'fade-in 180ms ease-out both',
      },
    },
  },
  plugins: [],
}
