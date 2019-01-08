# -*- coding: utf-8 -*-
# Zilliqa Mining Pool
# Copyright @ 2018-2019 Gully Chen
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

import logging
from datetime import datetime, timedelta
from jsonrpcserver import method

from mongoengine import Q

import zilpool
from zilpool.common import utils
from zilpool.pyzil import crypto
from zilpool.pyzil import ethash
from zilpool.database import pow, miner, zilnode


def init_apis(config):
    stats_config = config["api_server"]["stats"]

    @method
    async def stats():
        working_q = Q(expire_time__gte=datetime.utcnow()) & Q(finished=False)
        return {
            "version": zilpool.version,
            "utc_time": datetime.utcnow().isoformat(),
            "nodes": {
                "all": zilnode.ZilNode.count(),
                "active": zilnode.ZilNode.active_count(),
            },
            "miners": miner.Miner.count(),
            "workers": {
                "all": miner.Worker.count(),
                "active": miner.Worker.active_count(),
            },
            "works": {
                "all": pow.PowWork.count(),
                "working": pow.PowWork.count(working_q),
                "finished": pow.PowWork.count(finished=True),
                "verified": pow.PowResult.count(verified=True),
            },
        }

    @method
    async def stats_current():
        latest_work = pow.PowWork.get_latest_work()
        block_num = None
        difficulty = None
        start_time = None
        if latest_work:
            block_num = latest_work.block_num
            start_time = latest_work.start_time
            difficulty = ethash.boundary_to_difficulty(
                crypto.hex_str_to_bytes(latest_work.boundary)
            )

        now = datetime.utcnow()
        secs_next_pow = pow.PowWork.calc_seconds_to_next_pow()
        next_pow_time = now + timedelta(seconds=secs_next_pow)

        return {
            "block_num": block_num,
            "difficulty": difficulty,
            "utc_time": now.isoformat(),
            "start_time": start_time.isoformat(),
            "next_pow_time": next_pow_time.isoformat(),
        }

    @method
    @utils.args_to_lower
    async def stats_node(pub_key: str):
        pub_key = crypto.bytes_to_hex_str_0x(crypto.hex_str_to_bytes(pub_key))
        res = {"authorized": False}
        node = zilnode.ZilNode.get_by_pub_key(pub_key, authorized=None)
        if node:
            working_q = Q(expire_time__gte=datetime.utcnow()) & Q(finished=False)
            res.update({
                "authorized": node.authorized,
                "works": {
                    "all": pow.PowWork.count(pub_key=pub_key),
                    "working": pow.PowWork.count(working_q, pub_key=pub_key),
                    "finished": pow.PowWork.count(pub_key=pub_key, finished=True),
                    "verified": pow.PowResult.count(pub_key=pub_key, verified=True),
                }
            })

        return res

    @method
    @utils.args_to_lower
    async def stats_miner(wallet_address: str):
        res = {}
        m = miner.Miner.get(wallet_address=wallet_address)
        if m:
            last_work = pow.PowResult.get(miner_wallet=wallet_address,
                                          order="-finished_time")
            workers = [w.worker_name for w in m.workers]
            res.update({
                "authorized": m.authorized,
                "nick_name": m.nick_name,
                "rewards": m.rewards,
                "join_date": m.join_date.isoformat(),
                "last_finished_time": last_work.finished_time.isoformat(),
                "workers": workers,
                "works": m.works_stats(),
            })

        return res

    @method
    @utils.args_to_lower
    async def stats_worker(wallet_address: str, worker_name: str):
        res = {}
        worker = miner.Worker.get(wallet_address=wallet_address,
                                  worker_name=worker_name)
        if worker:
            last_work = pow.PowResult.get(miner_wallet=wallet_address,
                                          worker_name=worker_name,
                                          order="-finished_time")
            res.update({
                "miner": wallet_address,
                "worker_name": worker.worker_name,
                "last_finished_time": last_work.finished_time.isoformat(),
                "works": worker.works_stats(),
            })

        return res
