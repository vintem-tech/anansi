#!/usr/bin/env sh
set -eu

envsubst '${HOSTNAME}' < /'${ARCHITECTURE_TYPE}'.default.conf.template > /etc/nginx/conf.d/default.conf

exec "$@"