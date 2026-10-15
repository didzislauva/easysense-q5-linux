#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script as root: sudo $0" >&2
    exit 1
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LOGIN_USER=${SUDO_USER:-}

install -d -m 0755 /usr/local/lib/easysense-q5
install -m 0755 "$SCRIPT_DIR/easysense-q5-udev-bind" /usr/local/lib/easysense-q5/bind-driver
install -m 0644 "$SCRIPT_DIR/99-easysense-q5.rules" /etc/udev/rules.d/99-easysense-q5.rules

udevadm control --reload-rules
udevadm trigger --subsystem-match=usb --attr-match=idVendor=0403 --attr-match=idProduct=fe5c || true
/usr/local/lib/easysense-q5/bind-driver

if [ -n "$LOGIN_USER" ] && getent group dialout >/dev/null 2>&1; then
    usermod -aG dialout "$LOGIN_USER"
    echo "Added $LOGIN_USER to dialout; log out and back in for it to take effect."
fi

echo "EasySense Q5 Linux setup complete. Reconnect the logger if no tty appeared."
ls -l /dev/ttyUSB* 2>/dev/null || true
