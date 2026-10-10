/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        coffee: {
          espresso: '#2b1810',
          roast: '#3d2314',
          dark: '#4a2c1d',
          latte: '#b08968',
          caramel: '#d4a373',
          foam: '#ddbea9',
          cream: '#fbf7ee',
          paper: '#f5efe6',
          border: '#e8ded2',
        },
        amber: {
          badge: '#d97706',
          badgeBg: '#fef3c7',
        }
      },
      boxShadow: {
        'warm': '0 4px 20px -2px rgba(43, 24, 16, 0.08)',
        'warm-lg': '0 10px 25px -3px rgba(43, 24, 16, 0.12)',
      }
    },
  },
  plugins: [],
}
