#!/bin/bash
set -eux
HOST="pi@albatross-4"
PY="/home/pi/venv39/bin/python3"
TARGET="/tmp/weatherscreen"
rsync -avz . "$HOST:$TARGET"
ssh -t -t $HOST "\"$PY\" \"$TARGET/weatherscreen.py\""
