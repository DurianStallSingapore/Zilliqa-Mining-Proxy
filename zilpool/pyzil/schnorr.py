# -*- coding: utf-8 -*-
# Zilliqa Tools
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

import secrets
from hashlib import sha256
from typing import Optional

from fastecdsa import keys
from fastecdsa import point
from fastecdsa import curve


CURVE = curve.secp256k1
CURVE_BITS = 256
ENCODED_SIZE = CURVE_BITS // 8

SECP256K1_TAG_PUBKEY_EVEN = b"\x02"
SECP256K1_TAG_PUBKEY_ODD = b"\x03"
SECP256K1_TAG_PUBKEY_UNCOMPRESSED = b"\x04"


def gen_private_key() -> int:
    return keys.gen_private_key(CURVE)


def get_public_key(private_key: int) -> point.Point:
    return keys.get_public_key(private_key, CURVE)


def encode_signature(r: int, s: int, size=ENCODED_SIZE) -> bytes:
    r = r.to_bytes(size, "big")
    s = s.to_bytes(size, "big")
    return r + s


def decode_signature(signature: bytes) -> (int, int):
    size = len(signature) // 2
    r = int.from_bytes(signature[0:size], "big")
    s = int.from_bytes(signature[size:], "big")
    return r, s


def encode_public(x: int, y: int, compressed=True) -> bytes:
    if compressed:
        tag = SECP256K1_TAG_PUBKEY_ODD if (y & 0x01) else SECP256K1_TAG_PUBKEY_EVEN
        return tag + x.to_bytes(ENCODED_SIZE, "big")
    else:
        tag = SECP256K1_TAG_PUBKEY_UNCOMPRESSED
        return tag + x.to_bytes(ENCODED_SIZE, "big") + y.to_bytes(ENCODED_SIZE, "big")


def decode_public(pub_key: bytes) -> point.Point:
    try:
        if len(pub_key) == 33:
            # compressed format
            y_odd = pub_key[0:1] == SECP256K1_TAG_PUBKEY_ODD
            x = int.from_bytes(pub_key[1:], "big")

            y_y = pow(x, 3) + CURVE.a * x + CURVE.b
            y = mod_sqrt(y_y, CURVE.p, y_odd)

        elif len(pub_key) == 65:
            tag = pub_key[0:1]
            assert tag == SECP256K1_TAG_PUBKEY_UNCOMPRESSED

            x = int.from_bytes(pub_key[1:ENCODED_SIZE + 1], "big")
            y = int.from_bytes(pub_key[ENCODED_SIZE + 1:], "big")

        else:
            raise NotImplementedError

        return point.Point(x, y, CURVE)
    except:
        raise ValueError("The public key could not be parsed or is invalid")


def mod_sqrt(n: int, p: int, is_odd: bool) -> int:
    """ Find Square Root under Modulo p
    Given a number 'n' and a prime 'p', find square root of n under modulo p if it exists.
    https://www.geeksforgeeks.org/find-square-root-under-modulo-p-set-1-when-p-is-in-form-of-4i-3/
    """
    n %= p
    y = pow(n, (p + 1) // 4, p)

    y_odd = bool(y & 0x01)
    if y_odd != is_odd:
        y = p - y

    assert (y * y) % p == n
    return y


def sign(bytes_msg: bytes, bytes_private: bytes, retries=10) -> Optional[bytes]:
    for i in range(retries):
        k = secrets.randbelow(CURVE.q)
        if k == 0:
            continue
        signature = sign_with_k(bytes_msg, bytes_private, k)
        if signature:
            return signature
    return None


def sign_with_k(bytes_msg: bytes,
                bytes_private: bytes,
                k: int) -> Optional[bytes]:

    private_key = int.from_bytes(bytes_private, "big")

    order = CURVE.q

    Q = CURVE.G * k
    bytes_Q_x = encode_public(Q.x, Q.y)

    pub_key = keys.get_public_key(private_key, CURVE)
    bytes_pub_x = encode_public(pub_key.x, pub_key.y)

    hasher = sha256()
    hasher.update(bytes_Q_x + bytes_pub_x + bytes_msg)
    r = hasher.digest()
    r = int.from_bytes(r, "big") % order
    s = (k - r * private_key) % order
    if r == 0 or s == 0:
        return None

    return encode_signature(r, s)


def verify(bytes_msg: bytes,
           signature: bytes,
           bytes_public: bytes) -> bool:

    pub_key = decode_public(bytes_public)

    r, s = decode_signature(signature)
    n, G = CURVE.q, CURVE.G

    if not s or s >= n:
        return False
    if not r or r >= pow(2, CURVE_BITS):
        return False

    sG = s * G
    rW = r * pub_key
    Q = sG + rW

    bytes_Q_x = encode_public(Q.x, Q.y)
    bytes_pub_x = encode_public(pub_key.x, pub_key.y)

    hasher = sha256()
    hasher.update(bytes_Q_x + bytes_pub_x + bytes_msg)
    v = hasher.digest()
    v = int.from_bytes(v, "big")
    v = v % n

    return v == r
