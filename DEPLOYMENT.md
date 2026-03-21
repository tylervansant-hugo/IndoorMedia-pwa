# Deployment Guide - IndoorMedia PWA

This guide covers deploying the IndoorMedia PWA to production environments.

## Local Deployment (Development)

### 1. Install Dependencies
```bash
cd /Users/tylervansant/.openclaw/workspace/pwa
npm install
```

### 2. Run Both Services
```bash
npm run dev:full
```

- Frontend: http://localhost:5173
- Backend: http://localhost:3001

## Production Build

### 1. Build Frontend
```bash
npm run build
```

Creates optimized `dist/` folder with:
- Minified JavaScript
- Optimized CSS
- Service Worker
- Manifest file

### 2. Build Artifacts
```
dist/
├── index.html
├── assets/
│   ├── index-*.js
│   ├── index-*.css
│   └── ...
├── manifest.json
└── service-worker.js
```

## Server Deployment Options

### Option A: Node.js Server (Recommended)

#### Requirements
- Node.js 18+
- 512MB RAM
- Port 3001 access

#### Setup
```bash
# Install dependencies
npm install --production

# Build frontend
npm run build

# Copy built files to public/ (optional)
cp -r dist/* public/

# Start server
npm start
```

Server runs on `http://localhost:3001` (or configured PORT)

#### Environment Variables
```bash
export PORT=3001
export NODE_ENV=production
export NODE_TLS_REJECT_UNAUTHORIZED=0  # Only for self-signed certs
```

#### Systemd Service (Linux)
```ini
# /etc/systemd/system/indoormedia-pwa.service
[Unit]
Description=IndoorMedia PWA Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/deploy/indoormedia-pwa
Environment="NODE_ENV=production"
Environment="PORT=3001"
ExecStart=/usr/bin/node api-server.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
systemctl daemon-reload
systemctl enable indoormedia-pwa
systemctl start indoormedia-pwa
```

### Option B: Static Hosting + Separate API

If API server is hosted separately:

1. Deploy `dist/` to static hosting (Netlify, Vercel, S3)
2. Update API endpoint in `src/lib/api.js`
3. Configure CORS in `api-server.js`

### Option C: Docker

#### Dockerfile
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source
COPY . .

# Build frontend
RUN npm run build

# Expose port
EXPOSE 3001

# Start server
CMD ["npm", "start"]
```

#### Build and Run
```bash
docker build -t indoormedia-pwa:latest .
docker run -p 3001:3001 -e PORT=3001 indoormedia-pwa:latest
```

#### Docker Compose
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3001:3001"
    environment:
      NODE_ENV: production
      PORT: 3001
    volumes:
      - ./data:/app/data:ro
    restart: always
```

## Nginx Reverse Proxy

Configure Nginx to proxy requests to Node.js server:

```nginx
server {
    listen 80;
    server_name indoormedia.app;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name indoormedia.app;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/indoormedia.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/indoormedia.app/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;
    
    # Proxy to Node.js
    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Service worker - don't cache
    location = /service-worker.js {
        add_header Cache-Control "max-age=0, no-cache, no-store, must-revalidate";
    }
}
```

## Database & Data Files

### Setup
1. Ensure data files are accessible at:
   - `/Users/tylervansant/.openclaw/workspace/data/store-rates/stores.json`
   - `/Users/tylervansant/.openclaw/workspace/data/rep_registry.json`
   - `/Users/tylervansant/.openclaw/workspace/data/testimonials_cache.json`
   - `/Users/tylervansant/.openclaw/workspace/data/prospect_data.json`

2. Or update paths in `api-server.js` to match production locations

### File Permissions
```bash
chmod 644 /path/to/data/*.json
chmod 755 /path/to/data/
```

## HTTPS/SSL

### Let's Encrypt (Free)
```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d indoormedia.app

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Update Nginx with SSL paths
Edit `/etc/nginx/sites-available/indoormedia` and restart:
```bash
sudo systemctl reload nginx
```

## Performance Optimization

### 1. Enable Compression
- Nginx gzip (configured above)
- Node.js compression middleware (optional):
```javascript
import compression from 'compression';
app.use(compression());
```

### 2. Caching Strategy
- Static assets: 30 days
- Service worker: 0 days (no cache)
- API responses: vary by endpoint

### 3. CDN (Optional)
- Use Cloudflare or similar
- Cache static assets at edge
- DDoS protection

### 4. Database Connection Pooling
- Implement connection pooling if using database
- Current setup uses in-memory caching

## Monitoring & Logs

### Application Logs
```bash
# View logs (if using systemd)
journalctl -u indoormedia-pwa -f

# Or check Node.js logs
tail -f /var/log/indoormedia-pwa/app.log
```

### Health Monitoring
```bash
# Health check endpoint
curl https://indoormedia.app/api/health
```

### PM2 Process Manager (Optional)
```bash
# Install PM2
npm install -g pm2

# Start app
pm2 start api-server.js --name "indoormedia-pwa"

# Monitor
pm2 monit

# Logs
pm2 logs indoormedia-pwa
```

## Backup & Recovery

### Backup Data Files
```bash
#!/bin/bash
BACKUP_DIR="/backups/indoormedia-pwa"
DATA_DIR="/Users/tylervansant/.openclaw/workspace/data"

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/data-$(date +%Y%m%d).tar.gz $DATA_DIR

# Keep last 30 days
find $BACKUP_DIR -name "data-*.tar.gz" -mtime +30 -delete
```

### Restore from Backup
```bash
tar -xzf /backups/indoormedia-pwa/data-20240321.tar.gz -C /
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 3001
lsof -i :3001

# Kill process
kill -9 <PID>
```

### Memory Issues
```bash
# Monitor memory
top

# Increase Node heap size
export NODE_OPTIONS="--max-old-space-size=2048"
npm start
```

### Service Worker Issues
- Clear browser cache: Cmd+Shift+R (Mac) or Ctrl+Shift+R (PC)
- Disable service worker temporarily:
```javascript
// In index.html, comment out registration
// navigator.serviceWorker.register('/service-worker.js');
```

### API Connection Timeout
- Check firewall rules
- Verify port 3001 is open
- Check Nginx proxy configuration
- Review API server logs

## Performance Benchmarks

### Expected Response Times
- Login page: <500ms
- Store search: <1000ms (100+ results)
- Store detail: <300ms
- Cart operations: <100ms

### Expected Load
- Single server: 1000+ concurrent users
- With Nginx caching: 10000+ concurrent users
- With CDN: 100000+ concurrent users

## Rollback Plan

If deployment has issues:

1. Keep previous version running
2. Switch DNS/load balancer back to previous version
3. Investigate logs
4. Deploy fix
5. Test thoroughly before cutover

## Deployment Checklist

- [ ] All data files verified and accessible
- [ ] Environment variables set correctly
- [ ] HTTPS/SSL certificates installed
- [ ] Firewall rules updated
- [ ] Monitoring/alerting configured
- [ ] Backups enabled
- [ ] Load test completed
- [ ] User acceptance testing approved
- [ ] Deployment runbook prepared
- [ ] Rollback procedure tested

## Support

For deployment issues: tyler.vansant@indoormedia.com
