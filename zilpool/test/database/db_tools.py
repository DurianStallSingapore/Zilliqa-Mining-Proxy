# -*- coding: utf-8 -*-
# Zilliqa Mining Pool
# Copyright  @ 2018-2019 Gully Chen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# run "python setup.py develop" first

import os
import sys
import argparse

from zilpool.common import utils
from zilpool.database.basemodel import init_db, drop_collection
from zilpool.database import zilnode

cur_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(cur_dir)

config = utils.merge_config("debug.conf")

init_db(config)

all_collections = ["zil_nodes", "zil_pow_works", "zil_pow_results", "zil_miners"]


def drop_col(params=None):
    if not params:
        print(f"choice collections: {all_collections}")
        return
    if params[0] == "all":
        params = all_collections

    for col in params:
        res = drop_collection(col)
        print(f"{'PASSED' if res['ok'] else 'FAILED'} drop collection [{col}]: {res}")


def build_debug_db(params=None):
    import db_debug_data as debug

    print("add nodes")
    for node_data in debug.nodes:
        pub_key, pow_fee, authorized = node_data
        node = zilnode.ZilNode(pub_key=pub_key, pow_fee=pow_fee, authorized=authorized)
        res = node.save_to_db()
        print(f"create pub_key: {pub_key} result: {res}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="sub command: drop, create")
    parser.add_argument("params", nargs=argparse.REMAINDER)

    args = parser.parse_args()
    if args.command == "drop":
        drop_col(args.params)
    elif args.command == "create":
        build_debug_db(args.params)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
