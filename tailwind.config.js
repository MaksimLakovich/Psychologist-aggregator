/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // Django app templates
    "./users/templates/**/*.html",
    "./aggregator/templates/**/*.html",

    // JS (если используешь динамические классы)
    "./assets/js/**/*.js",
    "./static/js/**/*.js",
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
