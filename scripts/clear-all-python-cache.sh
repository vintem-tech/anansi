#!/bin/sh

cd ..
python3 -Bc "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
python3 -Bc "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"
find . -type f -name '.ipynb_checkpoints' -exec rm -rf {} +
find . -type d -name ".pytest_cache" -exec rm -rf "{}" \;
find . -type d -name ".ipynb_checkpoints" -exec rm -rf "{}" \;
