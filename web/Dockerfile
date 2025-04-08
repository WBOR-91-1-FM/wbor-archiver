# --- Build Stage ---
FROM node:18 as build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install

COPY . ./
RUN npm run build

# --- Production Stage (NGINX) ---
FROM nginx:stable-alpine

# Copy built static files from build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy a default NGINX config if needed; or rely on the existing
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
