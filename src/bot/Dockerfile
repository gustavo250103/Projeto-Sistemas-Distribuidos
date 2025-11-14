FROM node:20-bookworm

WORKDIR /app

# Instala dependências necessárias para compilar zeromq
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 build-essential pkg-config libzmq3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY package*.json ./
RUN npm install --only=production

COPY . .

CMD ["npm", "start"]
