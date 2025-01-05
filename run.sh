#! /bin/bash

VENV_FILE=./venv

echo "Checking virtual environment..."

if [ ! -d "$VENV_FILE" ]; then
  echo "Setting up virtual environment..."
  if command -v python &>/dev/null; then
    python -m venv venv
  elif command -v python3 &>/dev/null; then
    python3 -m venv venv
  else
    printf "\n\n\n *** Python not found! ***\n\n"
    PAUSE
  fi
  echo "Virtual environment: $VENV_FILE"
else
  echo "Activating virtual environment..."
  source ./venv/bin/activate
fi

echo "Installing Requirement Library..."
pip install -r requirements.txt

printf "\n\n\n *** SMTP Switcher ***\n\n"

echo "Starting SMTP Switcher server..."
python main.py "$@"