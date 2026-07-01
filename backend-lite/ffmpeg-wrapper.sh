#!/bin/sh
exec chroot /host /usr/bin/ffmpeg "$@"
