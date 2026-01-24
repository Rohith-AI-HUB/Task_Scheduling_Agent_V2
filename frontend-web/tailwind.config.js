/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "primary": "#7C5CFC",
        "background-light": "#F9FAFB",
        "background-dark": "#0F111A",
        "card-light": "#FFFFFF",
        "card-dark": "#1A1D2B",
        "surface": "#F9FAFB",
        "soft-purple": "#EDE9FE",
        "accent-purple": "#7C3AED",
      },
      fontFamily: {
        "sans": ["Plus Jakarta Sans", "sans-serif"],
        "display": ["Plus Jakarta Sans", "sans-serif"]
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "bento": "16px",
        "full": "9999px"
      },
    },
  },
  plugins: [],
}
