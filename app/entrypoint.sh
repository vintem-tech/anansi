#!/bin/sh

#! TODO: Deal with 'nc' dependency
#echo "Waiting for Influx..."

#while ! nc -z $INFLUXDB_HOST $INFLUXDB_PORT; do
#    echo "Influx not read"
#    sleep 3
#done

#echo "Influx started"
echo "sleeping"
sleep 30
echo "awaiking"

exec poetry run anansi
