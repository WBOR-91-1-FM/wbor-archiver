#!/bin/sh
envsubst '$FRONTEND_HOST $BACKEND_HOST $BACKEND_PORT $RMQ_HOST $PGADMIN_HOST' </etc/nginx/nginx.conf.template >/etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
