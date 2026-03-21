# Railway.app Deployment Guide

## Step 1: Create Railway Account
1. Go to https://railway.app
2. Click "Sign Up"
3. Use GitHub to sign up (easiest)
4. Authorize Railway to access your GitHub account

## Step 2: Create New Project
1. Click "Create New Project"
2. Select "GitHub Repo"
3. You'll need to push the PWA to GitHub first (see below)

## Step 3: Push to GitHub
```bash
cd /Users/tylervansant/.openclaw/workspace/pwa

# Initialize GitHub repo (if not already done)
git remote add origin https://github.com/YOUR_USERNAME/indoormedia-pwa.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## Step 4: Connect Repository to Railway
1. In Railway dashboard, click "New Project"
2. Select "GitHub Repo"
3. Find and select `indoormedia-pwa` repository
4. Railway will auto-detect it's a Node.js app

## Step 5: Configure Environment
Railway will automatically:
- Install dependencies (`npm install`)
- Build the app (`npm run build`)
- Start the server (`node api-server.js`)

## Step 6: Get Your Live URL
Once deployment completes:
- Railway gives you a public URL (like `indoormedia-pwa-production.up.railway.app`)
- Your PWA is now live! 🎉

## Step 7: Test on Mobile
1. Open the Railway URL on your iPad/iPhone/Android
2. Browser will show "Add to Home Screen" option
3. Tap it to install the PWA
4. App now works offline + can be updated automatically

## Cost
- Free tier: $5 credit/month (not enough)
- **Pay-as-you-go: $5-15/month** (recommended)
- Add credit card in Railway Settings

## Troubleshooting

**Build fails?**
- Check `npm run build` locally first
- Ensure all dependencies in package.json
- Check Node version (18+ required)

**App won't start?**
- Verify `api-server.js` is correct
- Check logs in Railway dashboard
- Ensure port 3001 is accessible

**Connection issues?**
- Check environment variables
- Verify data files are accessible
- Test locally first with `npm run dev:full`

## Next Steps
After deployment:
1. Share URL with reps: `https://your-railway-url.app`
2. They install PWA on home screen
3. App works on/offline, auto-updates
4. You can monitor usage in Railway dashboard

---

**Need help?** Check Railway docs: https://docs.railway.app
