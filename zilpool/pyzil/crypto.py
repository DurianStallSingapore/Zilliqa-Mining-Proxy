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

from collections import namedtuple
from functools import partial

import hashlib
import secrets
import coincurve


TOKEN_NUM_BYTES = 32
TOKEN_STR_LENGTH = TOKEN_NUM_BYTES * 2
ADDRESS_NUM_BYTES = 20     # address takes the last 20 bytes from hash digest of public key
ADDRESS_STR_LENGTH = ADDRESS_NUM_BYTES * 2


def rand_bytes(n_bytes=TOKEN_NUM_BYTES) -> bytes:
    if n_bytes <= 0:
        raise ValueError("0 and negative argument not allowed")
    return secrets.token_bytes(n_bytes)


def rand_hex_str(n_len=TOKEN_STR_LENGTH, prefix="") -> str:
    if n_len <= 0:
        raise ValueError("0 and negative argument not allowed")
    return prefix + (secrets.token_hex(n_len // 2 + 1)[:n_len])


def sha256(*bytes_hex, encoding="utf-8") -> bytes:
    m = hashlib.sha256()
    for b in bytes_hex:
        if isinstance(b, str):
            b = b.encode(encoding=encoding)
        m.update(b)
    return m.digest()


# hex string --> bytes
def hex_str_to_bytes(str_hex: str) -> bytes:
    str_hex = str_hex.lower()
    if str_hex.startswith("0x"):
        str_hex = str_hex[2:]
    if len(str_hex) & 1:
        str_hex = "0" + str_hex
    return bytes.fromhex(str_hex)


# bytes --> hex string
def bytes_to_hex_str(bytes_hex: bytes, prefix="") -> str:
    return prefix + bytes_hex.hex()


# bytes --> hex string with "0x"
bytes_to_hex_str_0x = partial(bytes_to_hex_str, prefix="0x")


# int number --> bytes
def int_to_bytes(i: int, n_bytes=TOKEN_NUM_BYTES, byteorder="big") -> bytes:
    if n_bytes is None:
        n_bytes = (i.bit_length() + 7) // 8 or 1
    return i.to_bytes(length=n_bytes, byteorder=byteorder)


# bytes --> int number
def bytes_to_int(bytes_hex: bytes, byteorder="big"):
    return int.from_bytes(bytes_hex, byteorder=byteorder)


# int number --> hex string
def int_to_hex_str(i: int, n_bytes=TOKEN_NUM_BYTES, prefix="", byteorder="big") -> str:
    return bytes_to_hex_str(int_to_bytes(i, n_bytes, byteorder), prefix=prefix)


# int number --> hex string with "0x"
int_to_hex_str_0x = partial(int_to_hex_str, prefix="0x")


# hex string --> int number
def hex_str_to_int(str_hex: str, byteorder="big"):
    return bytes_to_int(hex_str_to_bytes(str_hex), byteorder=byteorder)


KeyPair = namedtuple("KeyPair", ["public", "private"])
Point = namedtuple("Point", ["x", "y"])


class ZilKey:
    """ Zilliqa Keys """

    def __init__(self, str_pub=None, str_private=None):
        assert str_pub or str_private

        self.str_pub = str_pub
        self.str_private = str_private

        self.pub_key = None
        self.private_key = None

        self._generate_keys()

    def _generate_keys(self):
        if self.str_private:
            self.private_key = coincurve.PrivateKey.from_int(
                hex_str_to_int(self.str_private, "big")
            )

        if self.str_pub:
            self.pub_key = coincurve.PublicKey(
                hex_str_to_bytes(self.str_pub)
            )

        # check keys if set both
        if self.private_key and self.pub_key:
            assert self.private_key.public_key == self.pub_key, "public key mismatch"

        # generate pub_key if not set
        if self.private_key and not self.pub_key:
            self.pub_key = self.private_key.public_key

    @property
    def keypair_str(self):
        return KeyPair(bytes_to_hex_str(self.pub_key.format()),
                       self.private_key and self.private_key.to_hex())

    @property
    def keypair_bytes(self):
        return KeyPair(self.pub_key.format(),
                       self.private_key and self.private_key.secret)

    @property
    def keypair_int(self):
        return KeyPair(bytes_to_int(self.pub_key.format(), "big"),
                       self.private_key and self.private_key.to_int())

    @property
    def keypair_point(self):
        return KeyPair(Point(*self.pub_key.point()),
                       self.private_key and self.private_key.to_int())

    def __str__(self):
        return str(self.keypair_str)

    def __eq__(self, other):
        return self.pub_key == other.pub_key and self.private_key == other.private_key

    @property
    def address(self) -> str:
        m = hashlib.sha256()
        m.update(self.keypair_bytes.public)
        return m.hexdigest()[-ADDRESS_STR_LENGTH:]

    @classmethod
    def load_mykey_txt(cls, key_file="mykey.txt"):
        with open(key_file, "r") as f:
            str_pub, str_private = f.read().split()
            return ZilKey(str_pub=str_pub, str_private=str_private)

    @classmethod
    def generate_key_pair(cls):
        # generate new private key
        private_key = coincurve.PrivateKey(secret=None)
        zil_key = cls(str_private=private_key.to_hex())
        return zil_key
