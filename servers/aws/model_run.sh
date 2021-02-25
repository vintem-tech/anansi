#!/bin/bash

set -a
. /home/ec2-user/registry_login.env
set +a

docker login registry.gitlab.com -u $REGISTRY_USER -p $REGISTRY_PASSWORD

cd /home/ec2-user/application

echo "Your application is almost read to run!"

# docker-compose up -d

docker logout registry.gitlab.com

# sudo rm -rf /home/ec2-user/application/.env
# sudo rm -rf /home/ec2-user/application/registry_login.env
