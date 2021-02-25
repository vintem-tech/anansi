#!bin/sh

echo "[Unit]
Description=run_app
After=docker.service

[Service]
StartLimitInterval=0
Type=simple
Restart=no
RestartSec=1
User=ec2-user
ExecStart=/usr/bin/env bash /home/ec2-user/application/run.sh

[Install]
WantedBy=multi-user.target
" > run_app.service 

systemctl start run_app.service
systemctl enable run_app.service

mkdir -p application

touch application/.env application/docker-compose.yml

echo "REGISTRY_USER=
REGISTRY_PASSWORD=" > application/registry_login.env

echo "#!/bin/bash

set -a
. /home/ec2-user/registry_login.env
set +a

## Retrieves this instance's ID:
# instanceid=\`/usr/bin/curl -s http://169.254.169.254/latest/meta-data/instance-id\`

## Associates your elastic IP to this instance
# aws ec2 associate-address --region us-east-1 --instance-id \$instanceid --public-ip <your_IP>

docker login registry.gitlab.com -u \$REGISTRY_USER -p \$REGISTRY_PASSWORD

cd /home/ec2-user/application

echo 'Your application is almost read to run!'

# docker-compose up -d

docker logout registry.gitlab.com

# sudo rm -rf /home/ec2-user/application/.env
# sudo rm -rf /home/ec2-user/application/registry_login.env" > application/run.sh

chmod +x application/run.sh