#!/usr/bin/env bash

host="localhost:2525"
echo "Debug SMTP Server running at $host"
python -m smtpd -n -c DebuggingServer "$host"
