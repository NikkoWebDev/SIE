#!/usr/bin/env node
/**
 * compute-csp-hashes.mjs
 * Run after `npm run build` to recompute SHA-256 hashes for all is:inline scripts.
 * Paste the output into public/_headers replacing the existing sha256- entries.
 *
 * Usage: node scripts/compute-csp-hashes.mjs
 */
import { createHash } from 'crypto'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const htmlFile = path.join(root, 'dist', 'index.html')

const html = readFileSync(htmlFile, 'utf8')

// Match both nonce-bearing and plain is:inline scripts in output HTML
const re = /<script(?:\s+[^>]*)?>(\s*(?!<\/script)[\s\S]*?)<\/script>/g
let match
const hashes = new Set()

while ((match = re.exec(html)) !== null) {
  const content = match[1]
  // Skip empty scripts, JSON-LD, and module src scripts
  if (!content.trim() || match[0].includes('type="application/ld+json"') || match[0].includes('src=')) continue
  const hash = `'sha256-${createHash('sha256').update(content).digest('base64')}'`
  hashes.add(hash)
  console.log(`Script preview: ${JSON.stringify(content.trim().slice(0, 80))}`)
  console.log(`Hash: ${hash}\n`)
}

console.log('\n--- Paste into public/_headers script-src ---')
console.log(["'self'", "'strict-dynamic'", ...hashes].join(' '))
