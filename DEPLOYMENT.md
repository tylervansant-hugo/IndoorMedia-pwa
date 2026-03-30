# imPro Deployment Guide

## Current Setup: Vercel (100% Serverless)

This project is **exclusively deployed on Vercel**. No Railway, no Docker, no local servers.

### Architecture

**Frontend:**
- Vite static build → Vercel CDN
- Deployed at: `indoormedia-pwa.vercel.app`
- Auto-deploys on every push to `main` branch

**Backend:**
- Serverless functions in `/api/*.js`
- Runs on Vercel Functions (Node.js 18+)
- Google Places API proxy: `/api/search-places.js`

### Environment Variables

Required in Vercel:
- `GOOGLE_PLACES_API_KEY` - Google Places API key for nearby business search

Set via: Vercel Dashboard → Settings → Environment Variables

### Local Development

```bash
# Install dependencies
npm install

# Run Vite dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

**Note:** Serverless API functions won't run locally without Vercel CLI. For full local testing:
```bash
npm install -g vercel
vercel dev
```

### Deployment

Push to `main` branch → Vercel auto-deploys
- No manual builds needed
- No Docker required
- No Railway integration

### Migration from Railway

All Railway config has been removed:
- ❌ Dockerfile (removed)
- ❌ docker-compose.yml (removed)
- ❌ server.js / api-server.js (removed)
- ❌ railway.json (removed)
- ✅ vercel.json (added)

If you still receive Railway emails:
1. Go to Railway dashboard → https://railway.app
2. Delete the IndoorMedia project
3. Disconnect Railway GitHub integration
4. Check GitHub repo settings → Webhooks and remove any Railway webhooks

### Key Files

- `vercel.json` - Vercel configuration
- `api/search-places.js` - Google Places API proxy
- `src/` - Svelte components
- `public/` - Static assets
- `.gitignore` - Excludes deployment clutter (Dockerfile, server files, etc.)

### Support

For deployment issues:
- Check Vercel dashboard: https://vercel.com/dashboard
- View build logs: Dashboard → IndoorMedia PWA → Deployments
- Check function logs: Dashboard → Functions

---

**Status:** ✅ Fully migrated to Vercel. No external dependencies. No Railway.
