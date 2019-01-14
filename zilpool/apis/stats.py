# -*- coding: utf-8 -*-
# Zilliqa Mining Proxy
# Copyright (C) 2019  Gully Chen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


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
    @method
    async def stats():
        return summary()

    @method
    async def stats_current():
        return current_work()

    @method
    @utils.args_to_lower
    async def stats_node(pub_key: str):
        return node_stats(pub_key)

    @method
    @utils.args_to_lower
    async def stats_miner(wallet_address: str):
        return miner_stats(wallet_address)

    @method
    @utils.args_to_lower
    async def stats_worker(wallet_address: str, worker_name: str):
        return worker_stats(wallet_address, worker_name)

    @method
    @utils.args_to_lower
    async def stats_hashrate(block_num=None, wallet_address=None, worker_name=None):
        return hashrate_stats(block_num, wallet_address, worker_name)


#########################################
# Stats
#########################################
def summary():
    working_q = Q(expire_time__gte=datetime.utcnow()) & Q(finished=False)

    return {
        "version": zilpool.version,
        "utc_time": utils.iso_format(datetime.utcnow()),
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


def current_work():
    latest_work = pow.PowWork.get_latest_work()

    block_num = 0
    difficulty = 0
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
        "utc_time": utils.iso_format(now),
        "start_time": utils.iso_format(start_time),
        "next_pow_time": utils.iso_format(next_pow_time),
        "avg_hashrate": miner.HashRate.epoch_hashrate(block_num - 1),
        "avg_pow_fee": pow.PowWork.avg_pow_fee(block_num - 1),
    }


def node_stats(pub_key: str):
    pub_key = crypto.bytes_to_hex_str_0x(crypto.hex_str_to_bytes(pub_key))
    node = zilnode.ZilNode.get_by_pub_key(pub_key, authorized=None)
    if node:
        working_q = Q(expire_time__gte=datetime.utcnow()) & Q(finished=False)
        return {
            "authorized": node.authorized,
            "works": {
                "all": pow.PowWork.count(pub_key=pub_key),
                "working": pow.PowWork.count(working_q, pub_key=pub_key),
                "finished": pow.PowWork.count(pub_key=pub_key, finished=True),
                "verified": pow.PowResult.count(pub_key=pub_key, verified=True),
            }
        }


def miner_stats(wallet_address: str):
    m = miner.Miner.get(wallet_address=wallet_address)
    if m:
        last_work = pow.PowResult.get(miner_wallet=wallet_address,
                                      order="-finished_time")
        workers = [w.worker_name for w in m.workers]
        return {
            "authorized": m.authorized,
            "nick_name": m.nick_name,
            "rewards": m.rewards,
            "join_date": utils.iso_format(m.join_date),
            "last_finished_time": utils.iso_format(last_work and last_work.finished_time),
            "workers": workers,
            "works": m.works_stats(),
        }


def worker_stats(wallet_address: str, worker_name: str):
    worker = miner.Worker.get(wallet_address=wallet_address,
                              worker_name=worker_name)
    if worker:
        last_work = pow.PowResult.get(miner_wallet=wallet_address,
                                      worker_name=worker_name,
                                      order="-finished_time")
        return {
            "miner": wallet_address,
            "worker_name": worker.worker_name,
            "last_finished_time": utils.iso_format(last_work and last_work.finished_time),
            "works": worker.works_stats(),
        }


def hashrate_stats(block_num=None, wallet_address=None, worker_name=None):
    if block_num is None:
        block_num = pow.PowWork.get_latest_block_num()

    return {
        "block_num": block_num,
        "hashrate": miner.HashRate.epoch_hashrate(block_num, wallet_address, worker_name)
    }
