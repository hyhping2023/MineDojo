#!/bin/bash

set -euo pipefail

# iterate until a port is open
PORT="${1:-1044}"
MAX_RETRIES="${2:-120}"
echo >&1 "waiting for port $PORT to be open (max ${MAX_RETRIES} retries)"

retry=0
while [ $retry -lt "$MAX_RETRIES" ]; do
  nc -z 127.0.0.1 "$PORT" 2>/dev/null
  if [ $? -eq 0 ]; then
    break
  else 
    echo >&1 "port $PORT is still closed (attempt $((retry+1))/$MAX_RETRIES)"
    sleep 1
    retry=$((retry + 1))
  fi
done

if [ $retry -ge "$MAX_RETRIES" ]; then
  echo >&2 "ERROR: Timed out waiting for port $PORT to open."
  exit 1
fi

# add an extra sleep because we may be too fast detecting the port, and JVM crashes
sleep 3
