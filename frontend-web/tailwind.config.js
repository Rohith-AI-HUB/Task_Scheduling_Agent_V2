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
        "primary": "#7605cc",
        "background-light": "#f7f5f8",
        "background-dark": "#1a0f23",
        "surface": "#F3F4F6",
        "soft-purple": "#EDE9FE",
        "accent-purple": "#7C3AED",
      },
      fontFamily: {
        "sans": ["Inter", "sans-serif"],
        "display": ["Inter", "sans-serif"]
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
