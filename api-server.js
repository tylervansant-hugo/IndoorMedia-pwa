import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

console.log(`[STARTUP] Port: ${PORT}`);
console.log(`[STARTUP] __dirname: ${__dirname}`);

// Middleware
app.use(cors());
app.use(express.json());

// Static files
const distPath = path.join(__dirname, 'dist');
console.log(`[STARTUP] Dist path: ${distPath}`);
console.log(`[STARTUP] Dist exists: ${fs.existsSync(distPath)}`);

app.use(express.static(distPath));

// Mock data
const mockReps = {
  tyler: { id: 1, name: 'Tyler Van Sant', email: 'tyler.vansant@indoormedia.com' },
  amy: { id: 2, name: 'Amy Dixon', email: 'amy@indoormedia.com' },
  matt: { id: 3, name: 'Matt', email: 'matt@indoormedia.com' },
};

// Health check
app.get('/api/health', (req, res) => {
  console.log('[REQUEST] /api/health');
  res.json({ status: 'ok' });
});

// Rep registry endpoint
app.get('/api/rep-registry', (req, res) => {
  console.log('[REQUEST] /api/rep-registry');
  res.json(mockReps);
});

// Catch all - serve index.html
app.use((req, res) => {
  console.log(`[REQUEST] ${req.method} ${req.path}`);
  const indexPath = path.join(distPath, 'index.html');
  
  if (fs.existsSync(indexPath)) {
    console.log(`[RESPONSE] Serving index.html`);
    res.sendFile(indexPath);
  } else {
    console.log(`[ERROR] index.html not found at ${indexPath}`);
    res.status(404).send(`<h1>404</h1><p>index.html not found at ${indexPath}</p>`);
  }
});

// Start
const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`[SUCCESS] Server listening on 0.0.0.0:${PORT}`);
});

// Error handling
server.on('error', (err) => {
  console.error('[SERVER ERROR]', err);
});

process.on('uncaughtException', (err) => {
  console.error('[UNCAUGHT]', err);
  process.exit(1);
});
