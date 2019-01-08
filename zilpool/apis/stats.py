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
                "verified": pow.PowResult.count(verified_time=True),
            },
        }

    @method
    async def current():
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

        secs_next_pow = pow.PowWork.calc_seconds_to_next_pow()
        next_pow_time = datetime.utcnow() + timedelta(seconds=secs_next_pow)

        return {
            "block_num": block_num,
            "difficulty": difficulty,
            "start_time": start_time.isoformat(),
            "next_pow": next_pow_time.isoformat(),
        }

    @method
    async def stats_node(pub_key: str):
        pass
