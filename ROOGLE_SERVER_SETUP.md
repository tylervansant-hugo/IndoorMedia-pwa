# Roogle Scraper Server Setup

This is a local Node.js server that does real Roogle scraping for your PWA.

## Installation

1. **Install dependencies:**
   ```bash
   cd /Users/tylervansant/.openclaw/workspace/pwa
   npm install express cors puppeteer
   ```

2. **Start the server:**
   ```bash
   node roogle-server.js
   ```

   You should see:
   ```
   🚀 Roogle scraper server running at http://localhost:3001
   📡 API endpoint: http://localhost:3001/api/roogle-scraper
   ```

## How It Works

The server runs locally and:
1. Accepts requests from the PWA
2. Opens a real browser session
3. Logs into Roogle with your credentials
4. Searches for the store number
5. Navigates to Tape Info → Tape Contracts
6. Scrapes current and past contracts
7. Returns JSON to the PWA

## Updating the PWA

To use the local server instead of Vercel, update `ProspectSearch.svelte`:

Find this line:
```javascript
const response = await fetch(import.meta.env.BASE_URL + 'api/roogle-scraper', {
```

Change it to:
```javascript
const response = await fetch('http://localhost:3001/api/roogle-scraper', {
```

## Running on Your Mac

Keep the terminal open while using the PWA:
```bash
cd /Users/tylervansant/.openclaw/workspace/pwa
node roogle-server.js
```

The PWA will send requests to localhost:3001 and get real Roogle data.

## Stopping the Server

Press `Ctrl+C` in the terminal.
