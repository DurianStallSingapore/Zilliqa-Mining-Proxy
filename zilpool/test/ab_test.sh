#!/usr/bin/env bash

request=${1:-1000}
concurrency=${2:-10}
api=${3:-'zil_requestWork'}
url=${4:-'http://localhost:4202/api'}

ab -n ${request} -c ${concurrency} \
   -p "./data/${api}.json" \
   -T 'application/json' ${url}
