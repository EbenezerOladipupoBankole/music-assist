/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './App.tsx',
    './components/**/*.{ts,tsx}',
    './hooks/**/*.{ts,tsx}',
    './services/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        // font-serif was unwired - Merriweather loaded in index.html but
        // never actually applied; every heading fell back to system Georgia.
        serif: ['Merriweather', 'Georgia', 'Cambria', 'serif'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      fontSize: {
        // One consistent step for eyebrow/badge/label text, replacing the
        // scattered text-[8px]/[9px]/[10px]/[11px] arbitrary values.
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.08em' }],
      },
      boxShadow: {
        // A small, named elevation scale replacing one-off arbitrary shadow
        // values (shadow-[0_8px_30px_rgb(0,0,0,0.04)] etc.) scattered per
        // component with no shared vocabulary.
        subtle: '0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 1px rgba(15, 23, 42, 0.03)',
        elevated: '0 8px 24px -4px rgba(15, 23, 42, 0.08), 0 2px 8px -2px rgba(15, 23, 42, 0.04)',
        prominent: '0 24px 48px -12px rgba(15, 23, 42, 0.18), 0 8px 16px -8px rgba(15, 23, 42, 0.08)',
      },
    },
  },
  plugins: [],
};
