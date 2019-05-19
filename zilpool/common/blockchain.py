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

import asyncio
from datetime import datetime, timedelta

from cachetools import TTLCache

from zilpool.pyzil import zilliqa_api


class Zilliqa:
    config = None
    zil_conf = None
    api = None
    cache = None

    cur_tx_block = 0
    cur_ds_block = 0
    shard_difficulty = 0
    ds_difficulty = 0

    estimeted_pow_time = None

    tx_block_callbacks = []

    @classmethod
    def init(cls, conf):
        cls.config = conf
        cls.zil_conf = conf["zilliqa"]
        cls.api = zilliqa_api.API(cls.zil_conf["api_endpoint"])
        cls.cache = TTLCache(maxsize=64, ttl=cls.zil_conf["update_interval"])

    @classmethod
    def register_callback(cls, callback):
        cls.tx_block_callbacks.append(callback)

    @classmethod
    def remove_callback(cls, callback):
        while callback in cls.tx_block_callbacks:
            cls.tx_block_callbacks.remove(callback)

    @classmethod
    def run_callbacks(cls, cur_block):
        for callback in cls.tx_block_callbacks:
            asyncio.ensure_future(callback(cur_block))

    @classmethod
    async def get_cache(cls, key, func, *args, **kwargs):
        val = cls.cache.get(key)
        if val is None:
            val = await func(*args, **kwargs)
            try:
                cls.cache[key] = val
            except KeyError:
                pass
        return val

    @classmethod
    def clear_cache(cls, key=None):
        if key is None:
            cls.cache.clear()
        else:
            cls.cache.pop(key, None)

    @classmethod
    def calc_secs_to_pow(cls, txblock):
        block_per_pow = cls.zil_conf["BLOCK_PER_POW"]
        block_in_epoch = txblock % block_per_pow
        if block_in_epoch == 0:
            return 0
        return (block_per_pow - block_in_epoch) * cls.config.site_settings.avg_block_time

    @classmethod
    async def get_current_txblock(cls):
        block = await cls.get_cache("txblock", cls.api.GetCurrentMiniEpoch)
        block = int(block or 0)
        if block > cls.cur_tx_block:
            cls.cur_tx_block = block
            # update estimeted next pow time
            delta = timedelta(seconds=cls.calc_secs_to_pow(block))
            cls.estimeted_pow_time = datetime.utcnow() + delta

            cls.run_callbacks(cur_block=block)

        return block

    @classmethod
    async def get_current_dsblock(cls):
        block = await cls.get_cache("dsblock", cls.api.GetCurrentDSEpoch)
        block = int(block or 0)
        if block > cls.cur_ds_block:
            cls.cur_ds_block = block
        return block

    @classmethod
    async def get_difficulty(cls):
        shard_difficulty = await cls.get_cache("shard_difficulty",
                                               cls.api.GetPrevDifficulty)

        if shard_difficulty:
            cls.shard_difficulty = shard_difficulty
        return shard_difficulty

    @classmethod
    async def get_ds_difficulty(cls):
        ds_difficulty = await cls.get_cache("ds_difficulty",
                                            cls.api.GetPrevDSDifficulty)

        if ds_difficulty:
            cls.ds_difficulty = ds_difficulty
        return ds_difficulty

    @classmethod
    def is_pow_window(cls):
        if not cls.cur_tx_block:
            return False

        tx_block = cls.cur_tx_block
        block_per_pow = cls.zil_conf["BLOCK_PER_POW"]
        block_in_epoch = tx_block % block_per_pow
        return block_in_epoch in [0, block_per_pow - 1]

    @classmethod
    def secs_to_next_pow(cls):
        if not cls.cur_tx_block or not cls.estimeted_pow_time:
            return 0

        now = datetime.utcnow()
        if now > cls.estimeted_pow_time:
            delta = timedelta(seconds=cls.calc_secs_to_pow(cls.cur_tx_block))
            cls.estimeted_pow_time = now + delta

        return (cls.estimeted_pow_time - now).total_seconds()

    @classmethod
    async def update_chain_info(cls):
        tasks = [
            cls.get_current_txblock(),
            cls.get_current_dsblock(),
            cls.get_difficulty(),
            cls.get_ds_difficulty(),
        ]

        await asyncio.wait(tasks)

    @classmethod
    async def get_balance(cls, address):
        if address.startswith("0x"):
            address = address[2:]
        resp = await cls.get_cache(f"balance_{address}",
                                   cls.api.GetBalance,
                                   address)
        if not resp:
            return 0.0

        balance = int(resp["balance"])
        return balance / pow(10, 12)
