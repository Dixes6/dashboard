import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        border: 'var(--border)',
        text: 'var(--text)',
        muted: 'var(--muted)',
        primary: {
          DEFAULT: 'var(--primary)',
          soft: 'var(--primary-soft)',
          ink: 'var(--primary-ink)',
        },
        accent: 'var(--accent)',
        success: {
          DEFAULT: 'var(--success)',
          soft: 'var(--success-soft)',
          ink: 'var(--success-ink)',
        },
        danger: 'var(--danger)',
      },
      fontFamily: {
        heading: ['Cormorant', 'serif'],
        sans: ['Manrope', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
        btn: '12px',
      },
      boxShadow: {
        soft: '0 4px 20px -2px rgba(46, 35, 41, 0.05)',
      },
    },
  },
  plugins: [],
} satisfies Config
