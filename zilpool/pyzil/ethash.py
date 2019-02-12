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
"""
  ethash tools for Zilliqa
"""

import logging
from typing import List, Tuple, Optional, Union
from collections import OrderedDict

from . import crypto

from pyethash import (
    EPOCH_LENGTH,
    hashimoto_light,
    get_seedhash,
    mkcache_bytes,
)
from eth_hash.auto import keccak

MAX_EPOCH = 2048


def block_num_to_seed(block_number: int) -> bytes:
    return get_seedhash(block_number)


def seed_to_epoch_num(seed: bytes) -> int:
    for epoch in range(MAX_EPOCH):
        block_num = epoch * EPOCH_LENGTH + 1
        calc_seed = block_num_to_seed(block_num)
        if seed == calc_seed:
            return epoch
    raise ValueError("epoch number out of range, max 2048")


def seed_to_block_num(seed: bytes) -> int:
    return seed_to_epoch_num(seed) * EPOCH_LENGTH


ZERO_MASK = [0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01]


def difficulty_to_boundary(difficulty: int) -> bytes:
    boundary = bytearray(b"\xFF" * 32)
    n_bytes_to_zero = difficulty // 8
    n_bits_to_zero = difficulty % 8

    boundary[0:n_bytes_to_zero] = b"\x00" * n_bytes_to_zero
    boundary[n_bytes_to_zero] = ZERO_MASK[n_bits_to_zero]

    return bytes(boundary)


def boundary_to_difficulty(boundary) -> int:
    if isinstance(boundary, str):
        boundary = crypto.hex_str_to_bytes(boundary)

    difficulty = 0
    for b in memoryview(boundary):
        if b == 0:
            difficulty += 8
        else:
            difficulty += ZERO_MASK.index(b)
            break
    return difficulty


assert boundary_to_difficulty(difficulty_to_boundary(11)) == 11

dividend = 0xffff000000000000000000000000000000000000000000000000000000000000


def boundary_to_hashpower(boundary) -> int:
    if isinstance(boundary, str):
        return dividend // crypto.hex_str_to_int(boundary)
    elif isinstance(boundary, bytes):
        return dividend // crypto.bytes_to_int(boundary)
    raise TypeError("Type of boundary should be str or bytes")


def difficulty_to_hashpower(difficulty: int) -> int:
    return boundary_to_hashpower(difficulty_to_boundary(difficulty))


def is_less_or_equal(hash_1: Union[str, bytes],
                     hash_2: Union[str, bytes]) -> bool:
    if isinstance(hash_1, str):
        hash_1 = crypto.hex_str_to_bytes(hash_1)
    if isinstance(hash_2, str):
        hash_2 = crypto.hex_str_to_bytes(hash_2)

    assert isinstance(hash_1, bytes)
    assert isinstance(hash_2, bytes)

    return crypto.bytes_to_int(hash_1) <= crypto.bytes_to_int(hash_2)


# for pow verify
def verify_pow_work(block_number: int, header: bytes, mix_digest: bytes,
                    nonce: int, boundary: bytes) -> Optional[bytes]:

    calc_mix_digest, calc_result = pow_hash(block_number, header, nonce)

    if mix_digest != calc_mix_digest:
        logging.warning("mix_digest mismatch!")
        return None

    ok = is_less_or_equal(calc_result, boundary)
    if not ok:
        logging.warning("result not met the difficult")
        return None
    return calc_result


CACHE_MAX_ITEMS = 10
cache_seeds = bytearray(b"\x00" * 32)   # type: List[bytes]
cache_by_seed = OrderedDict()   # type: OrderedDict[bytes, bytearray]


def get_cache(block_number: int) -> bytes:
    while len(cache_seeds) <= block_number // EPOCH_LENGTH:
        cache_seeds.append(keccak(cache_seeds[-1]))
    seed = cache_seeds[block_number // EPOCH_LENGTH]
    if seed in cache_by_seed:
        c = cache_by_seed.pop(seed)  # pop and append at end
        cache_by_seed[seed] = c
        return c
    c = mkcache_bytes(block_number)
    cache_by_seed[seed] = c
    if len(cache_by_seed) > CACHE_MAX_ITEMS:
        cache_by_seed.popitem(last=False)  # remove last recently accessed
    return c


def pow_hash(block_number, header, nonce) -> Tuple[bytes, bytes]:
    cache_bytes = get_cache(block_number)
    hash_ret = hashimoto_light(block_number, cache_bytes, header, nonce)
    return hash_ret[b"mix digest"], hash_ret[b"result"]
