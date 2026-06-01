import type { APIRoute } from 'astro'
import { readdirSync, statSync, readFileSync } from 'fs'
import { join, resolve, normalize } from 'path'

const ASSETS_DIR = process.env.ASSETS_DIR || join(process.cwd(), 'public', 'assets')
const ASSETS_RESOLVED = resolve(ASSETS_DIR)

export const prerender = false

export const GET: APIRoute = async ({ url }) => {
  const fileParam = url.searchParams.get('file')
  if (fileParam) {
    const rawPath = normalize(fileParam).replace(/^(\.\.(\/|\\|$))+/, '')
    const filePath = resolve(join(ASSETS_RESOLVED, rawPath))
    if (!filePath.startsWith(ASSETS_RESOLVED)) {
      return new Response('Forbidden', { status: 403 })
    }
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
    const files = readdirSync(ASSETS_RESOLVED)
      .filter(f => f.endsWith('.jpg') || f.endsWith('.png'))
      .map(f => {
        const s = statSync(join(ASSETS_RESOLVED, f))
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
