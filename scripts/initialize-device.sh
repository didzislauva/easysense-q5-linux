#!/bin/sh
set -eu

VENDOR_ID=0403
PRODUCT_ID=fe5c
NEW_ID=/sys/bus/usb-serial/drivers/ftdi_sio/new_id

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script as root: sudo $0" >&2
    exit 1
fi

modprobe ftdi_sio

if [ ! -e "$NEW_ID" ]; then
    echo "ftdi_sio loaded, but $NEW_ID is unavailable" >&2
    exit 1
fi

# EEXIST means the ID was already registered and is harmless.
printf '%s %s\n' "$VENDOR_ID" "$PRODUCT_ID" >"$NEW_ID" 2>/dev/null || true

echo "EasySense Q driver initialized."
ls -l /dev/ttyUSB* 2>/dev/null || echo "Reconnect the Q5 to create /dev/ttyUSB0."
