/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{svelte,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // IndoorMedia brand colors
        primary: {
          50: '#f5f7fa',
          100: '#e8ecf1',
          200: '#c7d5e3',
          300: '#a6bdd5',
          400: '#5a7fa8',
          500: '#1a1a2e',
          600: '#0f0f1e',
          700: '#0a0a14',
          800: '#050509',
          900: '#000000',
        },
        accent: {
          50: '#ffe8e6',
          100: '#ffd6d2',
          200: '#ffada5',
          300: '#ff8578',
          400: '#ff5c4b',
          500: '#e74c3c',
          600: '#bf3f32',
          700: '#993228',
          800: '#73251e',
          900: '#4d1814',
        },
        slate: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['Menlo', 'monospace'],
      },
      boxShadow: {
        sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        DEFAULT: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
        md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        card: '0 2px 8px rgba(26, 26, 46, 0.15)',
      }
    },
  },
  plugins: [],
}
