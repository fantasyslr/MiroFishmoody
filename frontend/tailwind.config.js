/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        cream: '#f6f1e8',
        paper: '#fffdf8',
        stone: '#ebe2d6',
        line: '#d9cfc2',
        coffee: '#2f241d',
        ink: '#5c4b42',
        mist: '#7f93a1',
        'mist-soft': '#dfe7ea',
        wine: '#8c6167',
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', '"PingFang SC"', '"Hiragino Sans GB"', 'sans-serif'],
        serif: ['"Noto Serif SC"', 'serif'],
      },
      boxShadow: {
        paper: '0 18px 40px rgba(74, 58, 50, 0.08)',
        card: '0 10px 24px rgba(74, 58, 50, 0.08)',
        soft: '0 4px 12px rgba(74, 58, 50, 0.05)',
      },
      borderRadius: {
        panel: '28px',
      },
    },
  },
  plugins: [],
}
