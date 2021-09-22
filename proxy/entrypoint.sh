#!/usr/bin/env sh
set -eu
envsubst '${HOST_NAME}:${HOST_PORT}' < /$ARCHITECTURE_TYPE.template > /etc/nginx/conf.d/default.conf
rm -rf microservices.template monolithic.template
exec "$@"