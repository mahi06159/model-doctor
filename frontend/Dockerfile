FROM node:18-alpine

WORKDIR /app

# Copy package manifests first to leverage Docker cache
COPY package*.json /app/

# Install dependencies
RUN npm install

# Copy code
COPY . /app/

# Expose Vite default dev port
EXPOSE 5173

# Run Vite development server
CMD ["npm", "run", "dev"]
