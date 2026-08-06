import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { rm } from 'node:fs/promises'
import { resolve } from 'node:path'

// GitHub Pages has a 1GB per-site limit. The ~10k testimonial ad images in
// public/testimonial_ads (~1.1GB) blow that budget and make Pages builds error
// out, so we exclude them from the deployed bundle. They remain in the repo
// (main branch) and are served to the quote PDF from jsDelivr instead.
function excludeTestimonialAds() {
  return {
    name: 'exclude-testimonial-ads',
    apply: 'build',
    async closeBundle() {
      const dir = resolve(__dirname, 'dist/testimonial_ads')
      await rm(dir, { recursive: true, force: true })
      console.log('[build] Excluded dist/testimonial_ads from deploy (served via jsDelivr CDN).')
    },
  }
}

export default defineConfig({
  base: '/IndoorMedia-pwa/',
  plugins: [svelte(), excludeTestimonialAds()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser',
  },
  server: {
    port: 5173,
  },
})
