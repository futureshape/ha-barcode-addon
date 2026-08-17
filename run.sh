#!/usr/bin/with-contenv bashio

KBD_DEV=$(bashio::config 'keyboard_device')
BARCODE_API_KEY=$(bashio::config 'barcode_api_key')
PRINTER_ADDRESS=$(bashio::config 'printer_address')

export PYNPUT_BACKEND_KEYBOARD=uinput
export BARCODE_API_KEY="$BARCODE_API_KEY"
export PRINTER_ADDRESS="$PRINTER_ADDRESS"
export PYNPUT_BACKEND_MOUSE=dummy

echo "I am going to use $KBD_DEV as a keyboard device"
echo "Using Qutie printer address: ${PRINTER_ADDRESS:-not set}"

python3 /barcode.py