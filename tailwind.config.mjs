/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Sora', '-apple-system', 'BlinkMacSystemFont', 'SF Pro Text', 'Segoe UI', 'sans-serif'],
        display: ['Syne', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          maroon: '#800000',
          gold: '#fdc003',
          green: '#34d399',
          danger: '#ba1a1a',
        },
      },
      borderRadius: {
        apple: '10px',
        'apple-lg': '16px',
        'apple-xl': '20px',
        'apple-2xl': '28px',
      },
      boxShadow: {
        apple: '0 1px 3px rgba(0,0,0,0.04)',
        'apple-md': '0 4px 12px rgba(0,0,0,0.06)',
        'apple-lg': '0 8px 30px rgba(0,0,0,0.08)',
        'apple-dark': '0 1px 3px rgba(0,0,0,0.3)',
        'apple-dark-md': '0 4px 12px rgba(0,0,0,0.4)',
      },
      animation: {
        'fade-up': 'fadeUp 0.6s cubic-bezier(0.19,1,0.22,1)',
        'scale-in': 'scaleIn 0.4s cubic-bezier(0.34,1.56,0.64,1)',
        'shimmer': 'shimmer 1.8s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'spin-slow': 'spin 0.7s linear infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          '0%': { 'background-position': '-200% 0' },
          '100%': { 'background-position': '200% 0' },
        },
      },
    },
  },
  plugins: [],
}
