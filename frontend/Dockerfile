FROM nginx:alpine

# Remove default nginx index
RUN rm /usr/share/nginx/html/*

# Copy static page into the web root
COPY index.html /usr/share/nginx/html/index.html

# No need to expose or CMD; nginx base image handles it
