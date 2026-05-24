import { defineConfig } from 'astro/config'
import tailwind from '@astrojs/tailwind'
import vercel from '@astrojs/vercel'

export default defineConfig({
  output: 'static',
  adapter: vercel({}),
  integrations: [tailwind()],
  site: 'https://colegiociudaddelsol.edu.co',
  build: {
    inlineStylesheets: 'always',
  },
  vite: {
    build: {
      minify: 'esbuild',
    },
  },
})
