#!/usr/bin/with-contenv bashio

KBD_DEV=$(bashio::config 'keyboard_device')
BARCODE_API_KEY=$(bashio::config 'barcode_api_key')

export PYNPUT_BACKEND_KEYBOARD=uinput
export BARCODE_API_KEY="$BARCODE_API_KEY"
export PYNPUT_BACKEND_MOUSE=dummy

echo "I am going to use $KBD_DEV as a keyboard device"

python3 /barcode.py