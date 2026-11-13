/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          750: '#293548',
          850: '#151f32',
          950: '#090d16'
        }
      }
    },
  },
  plugins: [],
}
