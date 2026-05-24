module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        accent: 'var(--accent)',
        accent2: 'var(--accent-2)'
      },
      boxShadow: {
        'soft-lg': '0 6px 24px rgba(12,18,35,0.6)'
      }
    },
  },
  plugins: [],
}
