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
from collections import Mapping
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

from zilpool.pyzil import crypto

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


email_re = re.compile(r"\"?([-a-zA-Z0-9.`?{}]+@\w+\.\w+)\"?")


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


def iso_format(dt):
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + dt.strftime(".%f")[:4] + "Z"


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
