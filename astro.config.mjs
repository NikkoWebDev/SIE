import { defineConfig } from 'astro/config'
import tailwind from '@astrojs/tailwind'
import netlify from '@astrojs/netlify'
import sitemap from '@astrojs/sitemap'

export default defineConfig({
  output: 'static',
  adapter: netlify({}),
  integrations: [tailwind(), sitemap()],
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
