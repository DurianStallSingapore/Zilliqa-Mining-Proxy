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


import os
import re
import yaml
import hashlib
import asyncio
from datetime import datetime, timedelta
from collections import Mapping
from functools import wraps
from cachetools import TTLCache
from concurrent.futures import ThreadPoolExecutor

from zilpool.pyzil import crypto
from zilpool.pyzil import zilliqa_api

cur_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(cur_dir, "..")    # warning: take care


def app_path(*args) -> str:
    return os.path.join(app_dir, *args)


class MagicDict(dict):
    """ A dict with magic, you can access dict value like attributes. """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


def load_config(conf=app_path("default.conf")) -> MagicDict:
    """ Load configs from yaml file.
    :param conf: config filename
    :return: dict
    """
    with open(conf, "rb") as f:
        return MagicDict(yaml.load(f))


def merge_config(new_conf=None) -> MagicDict:
    """ Merge new configs with default.conf """
    config = load_config(app_path("default.conf"))
    if new_conf:
        new_config = load_config(new_conf)
        dict_merge(config, new_config)
    return MagicDict(config)


def dict_merge(dct, merge_dct) -> None:
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurse down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed, change inplace
    :param merge_dct: new dct merged into dct
    :return: None
    """
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], Mapping)):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


re_valid_str = re.compile(r"^[a-zA-Z0-9_.-]*$")


def is_valid_str(input_str: str) -> bool:
    return re_valid_str.match(input_str) is not None


def args_to_lower(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        args = [arg.lower() if isinstance(arg, str) else arg
                for arg in args]
        return func(*args, **kwargs)

    return wrapper


email_re = re.compile(r"\"?([a-zA-Z0-9.`?{}_+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+)\"?")


def valid_email(email: str):
    if email_re.match(email) is None:
        return None
    return email.strip().lower()


def valid_addr(wallet_addr: str):
    wallet_addr = wallet_addr.lower().strip()
    if not wallet_addr.startswith("0x"):
        wallet_addr = "0x" + wallet_addr

    if len(wallet_addr) != 2 + crypto.ADDRESS_STR_LENGTH:
        return None

    # noinspection PyBroadException
    try:
        crypto.hex_str_to_bytes(wallet_addr)
    except:
        return None
    return wallet_addr


def valid_pub_key(pub_key: str):
    # noinspection PyBroadException
    try:
        key = crypto.ZilKey(str_public=pub_key)
    except:
        return None
    return "0x" + key.keypair_str.public


def block_num_to_list(block_num=None):
    if block_num == "":
        block_num = None

    if block_num is None or isinstance(block_num, int):
        blocks = [block_num, ]
    elif isinstance(block_num, str):
        blocks = range_str_to_list(block_num)
    elif isinstance(block_num, (tuple, list)):
        blocks = block_num
    else:
        raise TypeError("Invalid block_num")
    return blocks


def range_str_to_list(range_str: str):
    range_list = []
    parts = range_str.split(",")
    for p in parts:
        if "-" in p:
            start, end = map(int, p.split("-", 2))
            step = 1 if start <= end else -1
            range_list.extend(range(start, end + step, step))
        else:
            num = int(p)
            range_list.append(num)

    return range_list


def iso_format(dt):
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + dt.strftime(".%f")[:4] + "Z"


def date_format(dt):
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")


SALT_SEP = "$"


def encrypt_password(password, salt=None, sep=SALT_SEP):
    assert isinstance(password, str)
    if salt is None:
        salt = crypto.rand_string(8)
    digest = f"{salt}{sep}{password}"

    salt_bytes = salt.encode()
    for i in range(10):
        digest = hashlib.sha256(salt_bytes + digest.encode()).hexdigest()

    return f"{salt}{sep}{digest}"


def verify_password(password, password_hash, sep=SALT_SEP):
    salt, digest = password_hash.split(sep, 2)

    return encrypt_password(password, salt, sep) == password_hash


def get_client_ip(request):
    try:
        ips = request.headers["X-Forwarded-For"]
    except KeyError:
        ips = request.transport.get_extra_info("peername")[0]
    return ips.split(',')[0]


_thread_pool = None


def get_thread_pool():
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor()
    return _thread_pool


def run_in_thread(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        thread_pool = get_thread_pool()
        return thread_pool.submit(func, *args, **kwargs)

    return wrapper


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

    @classmethod
    def init(cls, conf):
        cls.config = conf
        cls.zil_conf = conf["zilliqa"]
        cls.api = zilliqa_api.API(cls.zil_conf["api_endpoint"])
        cls.cache = TTLCache(maxsize=64, ttl=cls.zil_conf["update_interval"])

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
            return 0

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
