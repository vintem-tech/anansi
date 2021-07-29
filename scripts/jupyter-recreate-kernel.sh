#!/bin/sh

cd ./app
poetry run jupyter kernelspec remove anansi -y > REMOVE_JUPYTER_KERNEL 2>&1 &
rm -rf REMOVE_JUPYTER_KERNEL
exec poetry run python -m ipykernel install --user --name='anansi'
