#!/usr/bin/env bash
dir="`dirname $0`"
python "$dir/../mock_node/zil_simulator.py" keygen --keys "$dir/../mock_node/keys.txt"
python "$dir/../database/db_tools.py" --conf "$dir/../../../pool.conf" keys load "$dir/../mock_node/keys.txt"
python "$dir/../database/db_tools.py" --conf "$dir/../../../pool.conf" build

