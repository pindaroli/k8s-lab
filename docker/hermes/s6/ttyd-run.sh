#!/usr/bin/with-contenv bash
umask 0002
exec /usr/local/bin/ttyd \
  -p 7681 \
  -i 127.0.0.1 \
  -b /terminal \
  -W \
  -d 7 \
  -t fontSize=14 \
  -t fontFamily="JetBrains Mono, Menlo, monospace" \
  -t disableLeaveAlert=true \
  -w /opt/data \
  /bin/bash -l
