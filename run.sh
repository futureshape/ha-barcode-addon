#!/usr/bin/with-contenv bashio

KBD_DEV=$(bashio::config 'keyboard_device')

export PYNPUT_BACKEND_KEYBOARD=uinput
export PYNPUT_BACKEND_MOUSE=dummy

echo "I am going to use $KBD_DEV as a keyboard device"

python3 /barcode.py