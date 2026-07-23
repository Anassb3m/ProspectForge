/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html", "./app/static/js/**/*.js"],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50: "#eef7ff",
          100: "#d9ecff",
          500: "#2563eb",
          600: "#1d4ed8",
          700: "#1e40af",
          900: "#0f172a"
        },
        primary: {
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
        },
        surface: {
          100: '#1e293b',
          200: '#334155',
          300: '#475569',
        }
      },
      animation: {
        blob: "blob 7s infinite",
      },
      keyframes: {
        blob: {
          '0%': { transform: 'translate(0px, 0px) scale(1)' },
          '33%': { transform: 'translate(30px, -50px) scale(1.1)' },
          '66%': { transform: 'translate(-20px, 20px) scale(0.9)' },
          '100%': { transform: 'translate(0px, 0px) scale(1)' },
        }
      }
    }
  },
  plugins: []
};
