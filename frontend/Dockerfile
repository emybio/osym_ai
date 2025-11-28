# =============================================
# FRONTEND DOCKERFILE (OFFICE OPTIMIZED)
# =============================================
FROM node:22-alpine

WORKDIR /app

# Ofis ortamındaki NPM SSL problemlerini düzelt
RUN npm config set strict-ssl false
RUN npm config set registry http://registry.npmjs.org/
RUN npm cache clean --force

# Paket dosyalarını kopyala
COPY package*.json ./

# Bağımlılıkları kur
RUN npm install --legacy-peer-deps || npm install --force

# Kodlar docker-compose sırasında mount edilecek
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
