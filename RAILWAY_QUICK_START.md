# Railway Deployment - Quick Start (5 minutes)

## Prerequisites
- GitHub account (free at github.com)
- Credit card for Railway ($5-15/month)

## Step-by-Step

### 1. Create GitHub Repository
```bash
cd /Users/tylervansant/.openclaw/workspace/pwa

# Create new repo on github.com called "indoormedia-pwa"
# Then run:

git remote add origin https://github.com/YOUR_USERNAME/indoormedia-pwa.git
git branch -M main
git push -u origin main
```

### 2. Sign Up for Railway
1. Go to **https://railway.app**
2. Click "Sign Up"
3. Use **GitHub** to sign up
4. Authorize Railway

### 3. Deploy to Railway
1. In Railway dashboard, click **"Create New Project"**
2. Select **"GitHub Repo"**
3. Choose **"indoormedia-pwa"**
4. Railway auto-detects and deploys (takes 2-3 minutes)

### 4. Get Your Live URL
Once deployment shows "✓ Deployed":
- Copy the URL from the dashboard
- It looks like: `https://indoormedia-pwa-production.up.railway.app`

### 5. Test It Works
1. Open the URL on your iPad/iPhone/Android
2. Browser shows "Add to Home Screen"
3. Tap it → PWA installs on home screen
4. Now it works offline! 🎉

## Add Payment (Optional but Recommended)
1. In Railway, go to **Settings → Billing**
2. Add credit card
3. You'll be charged $5-15/month (only for what you use)

## Share with Reps
Send them your Railway URL:
```
"Download the IndoorMedia app here: https://your-url.railway.app"
```

That's it! You now have a live PWA! 🚀

---

**Still have questions?** See RAILWAY_DEPLOY.md for detailed troubleshooting.
