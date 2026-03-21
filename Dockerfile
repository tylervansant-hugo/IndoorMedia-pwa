FROM node:22-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application files
COPY . .

# Build Svelte app
RUN npm run build

# Start server
# Railway sets PORT env var, server uses it
CMD ["node", "api-server.js"]
