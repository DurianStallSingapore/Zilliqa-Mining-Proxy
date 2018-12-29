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
import time
import random
import argparse

from zilpool.common import utils
from zilpool.pyzil import crypto, ethash
from zilpool.database.basemodel import db, init_db, get_all_models, drop_all
from zilpool.database import zilnode, miner, pow
import zilpool.tests.database.db_debug_data as debug_data

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
    print("add nodes")
    for node_data in debug_data.nodes:
        pub_key, pow_fee, authorized = node_data
        if not pub_key.startswith("0x"):
            pub_key = "0x" + pub_key
        node = zilnode.ZilNode(pub_key=pub_key, pow_fee=pow_fee, authorized=authorized)
        res = node.save()
        print(f"create pub_key: {pub_key}")
        print(f"result: {res}")

    print("add miners")
    for wallet, worker in debug_data.miners:
        m = miner.Miner.get_or_create(wallet, worker)
        print(f"miner added: {m}")


def list_works(pub_key=None):
    if not pub_key:
        print("list all works")
        works = pow.PowWork.objects().all()
    else:
        print(f"list works from pub_key: {pub_key}")
        works = pow.PowWork.objects(pub_key=pub_key).all()

    for work in works:
        print(f"    {work}")


def add_new_work(block_num, difficulty, timeout, node=0):
    print(f"Generate a work for block {block_num}, difficulty {difficulty}")
    header = crypto.rand_hex_str_0x(64)
    seed = crypto.bytes_to_hex_str_0x(ethash.block_num_to_seed(block_num))
    boundary = crypto.bytes_to_hex_str_0x(ethash.difficulty_to_boundary(difficulty))

    print(f"    header    : {header}")
    print(f"    seed      : {seed}")
    print(f"    boundary  : {boundary}")

    pub_key = debug_data.nodes[node][0]
    print(f"save work, timeout = {timeout}, pub_key = {pub_key}")
    work = pow.PowWork.new_work(header, seed, boundary,
                                pub_key=pub_key, signature="",
                                timeout=timeout)
    work = work.save()
    if work:
        print(f"success, {work}")
    else:
        print(f"failed")


def build_pow_work(params=None):
    if not params:
        print("sub commands:")
        print("    new [block_num] [difficulty] [timeout]")
        print("    demo [block_num] [difficulty] [timeout]")
        print("    list [pub_key]")
        return

    if params[0] == "new":
        print("work new [block_num] [difficulty] [timeout]")
        block_num = int(params[1]) if len(params) > 1 else 42
        difficulty = int(params[2]) if len(params) > 2 else 5
        timeout = int(params[3]) if len(params) > 3 else 600

        add_new_work(block_num, difficulty, timeout)
    elif params[0] == "list":
        pub_key = params[1] if len(params) > 1 else None
        list_works(pub_key)
    elif params[0] == "demo":
        print("work demo [block_num] [difficulty] [timeout]")
        print("start loop to create new work")
        block_num = int(params[1]) if len(params) > 1 else 0
        difficulty = int(params[2]) if len(params) > 2 else 25
        timeout = int(params[3]) if len(params) > 3 else 600
        while True:
            for i in range(5):
                difficulty = random.randrange(-5, 5) + difficulty
                timeout = random.randrange(-60, 60) + timeout
                node = random.randrange(0, len(debug_data.nodes))
                if difficulty < 0:
                    difficulty = 0
                if timeout < 0:
                    timeout = 0

                add_new_work(block_num, difficulty, timeout, node)
                sec = random.randrange(0, 30)
                print(f"sleep {sec} seconds ......")
                time.sleep(sec)

            block_num += 1


def show_miners(params=None):
    if not params:
        print("sub commands:")
        print("    list [wallet]")
        return

    def list_miners():
        wallet = params[1] if len(params) > 1 else None
        if not wallet:
            print("list all miners")
            miners = miner.Miner.objects().all()
            for m in miners:
                print(f"    {m}")
        else:
            print(f"list workers of miner: {wallet}")
            m = miner.Miner.objects(wallet_address=wallet).first()
            if m is None:
                print("  miner not found")
                return
            print(f"  {m}")
            workers = miner.Worker.objects(wallet_address=wallet).all()
            for worker in workers:
                print(f"    {worker}")

    if params[0] == "list":
        list_miners()


def keypairs(params=None):
    if not params:
        print("sub commands:")
        print("    load [file_path]              # batch load node keys to database")
        print("    gen  [file_path] [num_nodes]  # batch generate node keys to file")
        return

    def load_keys(file_path):
        keys = []

        if not os.path.isfile(file_path):
            print(f"keys file not found, pls run 'keys gen' first")
            exit(1)

        with open(file_path, "r") as f:
            for line in f.readlines():
                parts = line.strip().split(",")
                if len(parts) < 1:
                    print(f"Invalid Key in {line}")
                    continue
                public = parts[0]
                private = None
                if len(parts) > 1:
                    private = parts[1]

                key = crypto.ZilKey(str_public=public, str_private=private)
                keys.append(key)

        print("add nodes")
        for key in keys:
            pub_key, pow_fee, authorized = key.keypair_str.public, 0.0, True
            if not pub_key.startswith("0x"):
                pub_key = "0x" + pub_key
            node = zilnode.ZilNode(pub_key=pub_key, pow_fee=pow_fee, authorized=authorized)
            node = node.save()
            print(f"create node: {node}")

    def gen_keys(file_path, num_nodes=10):
        print(f"Starting to generate keypairs for ZIL nodes")
        keys = []
        for i in range(num_nodes):
            key = crypto.ZilKey.generate_key_pair()
            keys.append(",".join(key.keypair_str))

        with open(file_path, "w") as f:
            f.write("\n".join(keys))

        print(f"{len(keys)} keypairs generated into > {file_path}")

    if params[0] == "load":
        keys_file = params[1] if len(params) > 1 else "keys.txt"
        load_keys(keys_file)

    elif params[0] == "gen":
        _file = params[1] if len(params) > 1 else "keys.txt"
        _nodes = int(params[2]) if len(params) > 2 else 10
        gen_keys(_file, _nodes)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="sub command: drop, build, work, miner")
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
    elif args.command == "build":
        build_debug_db(args.params)
    elif args.command == "work":
        build_pow_work(args.params)
    elif args.command == "miner":
        show_miners(args.params)
    elif args.command == "keys":
        keypairs(args.params)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
