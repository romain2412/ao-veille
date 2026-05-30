/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f9f0',
          100: '#dcf0dc',
          500: '#2d7a2d',
          600: '#246124',
          700: '#1b4a1b',
        },
      },
    },
  },
  plugins: [],
}
