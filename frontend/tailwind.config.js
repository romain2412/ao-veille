/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Poppins', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#f0f7f5',
          100: '#c2e1d1',   // vert clair
          200: '#90CFB0',   // vert menthe (#90CFB0)
          300: '#5aad8a',
          500: '#053F33',   // vert principal FB VRD
          600: '#042e25',
          700: '#031e18',
        },
        fbgray: '#F2F2F2',   // fond général
        fbtext: '#262626',   // texte principal
        fbslate: '#637477',  // texte secondaire
      },
      borderRadius: {
        pill: '25px',
      },
    },
  },
  plugins: [],
}
