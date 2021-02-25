#!/bin/bash

set -a
. /home/ec2-user/application/registry_login.env
set +a

## Retrieves this instance's ID:
# instanceid=`/usr/bin/curl -s http://169.254.169.254/latest/meta-data/instance-id`

## Associates your elastic IP to this instance
# aws ec2 associate-address --region us-east-1 --instance-id $instanceid --public-ip <your_IP>

docker login registry.gitlab.com -u $REGISTRY_USER -p $REGISTRY_PASSWORD

cd /home/ec2-user/application

echo 'Your application is almost read to run!'

# docker-compose up -d

docker logout registry.gitlab.com

# sudo rm -rf /home/ec2-user/application/.env
# sudo rm -rf /home/ec2-user/application/registry_login.env
