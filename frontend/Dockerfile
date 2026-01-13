FROM node:22-alpine
WORKDIR /app

ENV NODE_ENV=development \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json* ./
RUN npm install --ignore-scripts

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]