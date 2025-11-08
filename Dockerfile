# ===== Base image =====
FROM node:18 AS base
WORKDIR /app

# ===== Catalog microservice =====
FROM base AS production
RUN apt-get update && apt-get install -y sqlite3
COPY ./main/catalog-microservice/package*.json ./
RUN npm install --only=production
COPY ./main/catalog-microservice .
CMD ["npm", "run", "start-catalog"]

# ===== Order microservice =====
FROM base AS production1
RUN apt-get update && apt-get install -y sqlite3
COPY ./main/order-microservice/package*.json ./
RUN npm install --only=production
COPY ./main/order-microservice .
CMD ["npm", "run", "start-order"]

# ===== Client microservice =====
FROM base AS client
COPY ./main/client-microservice/package*.json ./
RUN npm install --only=production
COPY ./main/client-microservice .
CMD ["npm", "run", "start-client"]
