#!/bin/bash
exec google-chrome --headless --no-sandbox --disable-gpu --remote-debugging-port=9222 "$@"
