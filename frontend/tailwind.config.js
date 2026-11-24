/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./static/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        canvas: '#FFFFFF',
        canvasSubtle: '#F8FAFC',
        canvasMuted: '#F1F5F9',
        borderSubtle: '#E2E8F0',
        borderStrong: '#CBD5E1',
        slateTextPrimary: '#0F172A',
        slateTextSecondary: '#475569',
        slateTextMuted: '#94A3B8',
        accentGreen: '#059669',
        accentAmber: '#D97706',
        accentRose: '#E11D48',
        brandBlack: '#0F172A',
      }
    },
  },
  plugins: [],
}

