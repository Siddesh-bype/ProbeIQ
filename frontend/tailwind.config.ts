import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary:     '#1E3A5F',
        secondary:   '#2563EB',
        accent:      '#059669',
        background:  '#F8FAFC',
        foreground:  '#0F172A',
        muted:       '#F1F3F5',
        border:      '#E4E7EB',
        destructive: '#DC2626',
      },
    },
  },
  plugins: [],
}
export default config
