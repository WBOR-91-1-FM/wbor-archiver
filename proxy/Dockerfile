FROM nginx:stable-alpine

# Copy the templated Nginx configuration
COPY nginx.conf.template /etc/nginx/nginx.conf.template

# Copy the entrypoint script that substitutes environment variables and starts Nginx
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

# Use the custom entrypoint to generate the final nginx.conf and launch Nginx
CMD ["/docker-entrypoint.sh"]
