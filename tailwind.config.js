/** @type {import('tailwindcss').Config} */
module.exports = {
  // Archivos donde Tailwind buscará clases para generar el CSS final.
  content: [
    './templates/**/*.html',
    './core/**/*.py'
  ],
  theme: {
    extend: {
      // Paleta personalizada para darle identidad visual al proyecto.
      colors: {
        // Azul principal para botones y encabezados.
        brand: {
          50: '#eef4ff',
          100: '#dbe8ff',
          500: '#4f7dff',
          600: '#3d68e5',
          700: '#3153bb',
          900: '#1f2f6a'
        },
        // Acabado cálido para acentos tipo promociones/gradientes.
        sunset: {
          50: '#fff4ef',
          100: '#ffe4d6',
          500: '#ff8a5c',
          600: '#ef6f3f'
        },
        // Tonos frescos de apoyo para fondos suaves y detalles.
        ocean: {
          50: '#ecfeff',
          100: '#cffafe',
          500: '#06b6d4',
          600: '#0891b2'
        }
      }
    }
  },
  // Lista de plugins Tailwind (de momento vacío, pero listo para crecer).
  plugins: []
};
