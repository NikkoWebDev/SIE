#!/usr/bin/env bash
set -euo pipefail

echo "==> Instalando dependencias"
npm install

echo "==> Construyendo SSG estático"
npm run build

echo "==> Desplegando a Vercel"
npx vercel --prod --yes

echo "==> Hecho"
