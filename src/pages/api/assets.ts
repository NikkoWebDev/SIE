import type { APIRoute } from 'astro'
import { readdirSync, statSync, readFileSync } from 'fs'
import { join } from 'path'

const ASSETS_DIR = '/home/niko/Proyectos/C sol/Scripts/colegio_assets'

export const prerender = false

export const GET: APIRoute = async ({ url }) => {
  const fileParam = url.searchParams.get('file')
  if (fileParam) {
    const filePath = join(ASSETS_DIR, fileParam)
    try {
      const buf = readFileSync(filePath)
      const ext = filePath.endsWith('.png') ? 'png' : 'jpeg'
      return new Response(buf, {
        headers: {
          'Content-Type': `image/${ext}`,
          'Cache-Control': 'public, max-age=31536000, immutable',
        },
      })
    } catch {
      return new Response('Not found', { status: 404 })
    }
  }
  try {
    const files = readdirSync(ASSETS_DIR)
      .filter(f => f.endsWith('.jpg') || f.endsWith('.png'))
      .map(f => {
        const s = statSync(join(ASSETS_DIR, f))
        return { name: f, size: s.size }
      })
    return new Response(JSON.stringify(files), {
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    return new Response(JSON.stringify([]), {
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
