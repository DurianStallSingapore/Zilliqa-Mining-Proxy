#!/usr/bin/env bash

request=${1:-1000}
concurrency=${2:-10}
api=${3:-'zil_requestWork'}
url=${4:-'http://127.0.0.1:4202/api'}

ab -n ${request} -c ${concurrency} \
   -p "./post_data/${api}.json" \
   -T 'application/json' ${url}
