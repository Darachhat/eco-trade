/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#080a0f',
          panel: '#0d1117',
          surface: '#161b22',
          card: '#0f141c',
          elevated: '#1a202c',
          border: '#21262d',
          borderSubtle: '#181d24',
          highlight: '#2d333b',
          text: '#e6edf3',
          muted: '#8b949e',
          dim: '#484f58',
          cyan: '#06b6d4',
          cyanGlow: '#0891b2',
          bull: '#10b981',
          bullDim: 'rgba(16, 185, 129, 0.12)',
          bullBorder: 'rgba(16, 185, 129, 0.3)',
          bear: '#f43f5e',
          bearDim: 'rgba(244, 63, 94, 0.12)',
          bearBorder: 'rgba(244, 63, 94, 0.3)',
          amber: '#f59e0b',
          amberDim: 'rgba(245, 158, 11, 0.12)',
          purple: '#a855f7',
          purpleDim: 'rgba(168, 85, 247, 0.12)',
          blue: '#3b82f6',
          blueDim: 'rgba(59, 130, 246, 0.12)',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      fontSize: {
        '2xs': '0.65rem',
        'xs': '0.725rem',
        'sm': '0.8rem',
        'base': '0.875rem',
        'lg': '1rem',
        'xl': '1.125rem',
        '2xl': '1.25rem',
      },
      letterSpacing: {
        terminal: '0.025em',
        widest: '0.1em',
      },
      boxShadow: {
        'terminal-card': '0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px -1px rgba(0, 0, 0, 0.4)',
        'cyan-glow': '0 0 15px rgba(6, 182, 212, 0.25)',
        'bull-glow': '0 0 15px rgba(16, 185, 129, 0.25)',
        'bear-glow': '0 0 15px rgba(244, 63, 94, 0.25)',
      },
    },
  },
  plugins: [],
}
