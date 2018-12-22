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
from zilpool.database.basemodel import db, init_db, get_all_models, drop_all
from zilpool.database import zilnode

cur_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(cur_dir)


def drop_col(params=None, force=False):
    all_collections = [cls._get_collection_name() for cls in get_all_models()]

    if not params:
        print(f"pls choice collections: {all_collections}")
        return

    def confirm():
        ans = "y"
        if not force:
            ans = input(f"Are you sure to drop data y/N? ")
        return ans == "y"

    if params[0] == "all":
        print("drop all collections")
        if confirm():
            print("Done")
            drop_all()
        else:
            print("Skipped")
        return

    for col in params:
        db_collection = db.get_collection(col)

        print(f"drop collection {db_collection.name}")
        if confirm():
            db_collection.drop()
            print("Done")
        else:
            print("Skipped")


def build_debug_db(params=None):
    import db_debug_data as debug

    print("add nodes")
    for node_data in debug.nodes:
        pub_key, pow_fee, authorized = node_data
        node = zilnode.ZilNode(pub_key=pub_key, pow_fee=pow_fee, authorized=authorized)
        res = node.save()
        print(f"create pub_key: {pub_key} result: {res}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="sub command: drop, create")
    parser.add_argument("--conf", help="conf file", default="debug.conf")
    parser.add_argument("params", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    args.conf = os.path.abspath(args.conf)
    print(f"config file: {args.conf}")
    config = utils.merge_config(args.conf)
    print(f"database: {config.database['uri']}")
    init_db(config)

    if args.command == "drop":
        drop_col(args.params, force=False)
    elif args.command == "create":
        build_debug_db(args.params)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
