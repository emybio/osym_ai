
FROM node:22-alpine

WORKDIR /app

# Sadece package.json kopyalanır ve bağımlılıklar kurulur
COPY package*.json ./
RUN npm install

# Kod mount edileceği için COPY gerekmez
ENV NODE_ENV=development

# Vite canlı sunucu
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
