#!/bin/sh

cd ./app
poetry env remove python > TRY_TO_REMOVE_POETRY_ENV 2>&1 &
rm -rf poetry.lock TRY_TO_REMOVE_POETRY_ENV
exec poetry install
