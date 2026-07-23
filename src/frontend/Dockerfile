FROM node:20-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM dependencies AS builder
COPY . .
RUN npm run build
RUN npm prune --omit=dev

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/src/frontend/.next ./src/frontend/.next
COPY --from=builder /app/src/frontend/next.config.mjs ./src/frontend/next.config.mjs
EXPOSE 3000
CMD ["npm", "run", "start"]
