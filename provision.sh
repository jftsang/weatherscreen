#!/bin/bash
VENV="$HOME/venv39"
set -eux
sudo apt update
sudo apt install -y python3-venv libatlas3-base git build-essential libopenjp2-7
sudo raspi-config nonint do_spi 0

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"

cd $HOME
if [ ! -d "weatherscreen" ]; then
  git clone "https://github.com/jftsang/weatherscreen.git"
fi
cd weatherscreen
git pull --ff-only
pip install -r requirements.txt
python3 weatherscreen.py
