/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: "#1A1220",      // Soft blush-lavender dark background
          card: "#2A1F30",    // Lavender-tinted card surface
          border: "#3D2F42",  // Warm purple border
          accent: "#F472B6",  // Rose-400 for accents
          success: "#4ADE80", // Warmer emerald
          warning: "#FBBF24", // Warmer amber
          danger: "#F87171"   // Warmer red
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Poppins', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
