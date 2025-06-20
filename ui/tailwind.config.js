/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // This line ensures Tailwind scans all relevant files in src
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
