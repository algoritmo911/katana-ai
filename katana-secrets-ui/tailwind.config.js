/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // Scan all relevant files in src
  ],
  theme: {
    extend: {
      // You can extend the default Tailwind theme here if needed
      // For example:
      // colors: {
      //   'katana-blue': '#1e3a8a',
      // },
    },
  },
  plugins: [
    // You can add Tailwind plugins here if needed
    // require('@tailwindcss/forms'),
  ],
}
