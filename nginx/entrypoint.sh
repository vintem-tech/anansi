#!/usr/bin/env sh
set -eu

envsubst '${HOSTNAME}' < /default.conf.template > /etc/nginx/conf.d/default.conf

exec "$@"