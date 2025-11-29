/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // Django app templates
    "./users/templates/**/*.html",
    "./aggregator/templates/**/*.html",
    "./core/templates/**/*.html",

    // в Tailwind по умолчанию включена оптимизация и поэтому если:
    // а) SVG находится внутри HTML то значит purge не удалит классы и все ок
    // б) Но! если SVG находится в отдельном файле вне указанных путей например /templates/components/ то
    // purge удалит классы и SVG отобразится некорректно
    // ПОЭТОМУ для использования SVG в /templates/components/ нужно добавить это:
    './templates/**/*.html',
    './templates/components/**/*.html',

    // JS (если используешь динамические классы)
    "./assets/js/**/*.js",
    "./static/js/**/*.js",
    "./node_modules/flowbite/**/*.js"

  ],

  theme: {
    extend: {
      colors: {
        primary: {
        "50":"#fdf2f8","100":"#fce7f3","200":"#fbcfe8",
        "300":"#f9a8d4","400":"#f472b6","500":"#ec4899",
        "600":"#db2777","700":"#be185d","800":"#9d174d","900":"#831843","950":"#500724"}
      }
    },
  },

  plugins: [
    require('@tailwindcss/forms'),
    require('flowbite/plugin'),
    require('flowbite-typography'),
  ],
}
