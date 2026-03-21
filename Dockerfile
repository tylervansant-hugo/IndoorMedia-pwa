FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application files
COPY . .

# Build Svelte app
RUN npm run build

# Expose port
EXPOSE 3001

# Start server
CMD ["node", "api-server.js"]
