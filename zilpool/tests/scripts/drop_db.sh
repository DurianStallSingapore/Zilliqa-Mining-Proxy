#!/usr/bin/env bash
dir="`dirname $0`"
python "$dir/../database/db_tools.py" --conf "$dir/../../../pool.conf" drop all
