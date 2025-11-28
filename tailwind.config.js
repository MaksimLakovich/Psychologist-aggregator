/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./users/_web/templates/**/*.html",
    "./aggregator/_web/templates/**/*.html",
    "./users/_web/**/*.js",
    "./aggregator/_web/**/*.js",
    "./static/**/*.js",
    "./static/**/*.css",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('flowbite/plugin'),
    require('flowbite-typography'),
  ],
}
