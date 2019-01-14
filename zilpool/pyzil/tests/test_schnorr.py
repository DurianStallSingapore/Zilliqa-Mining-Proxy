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
import json
import random

import pytest

from zilpool.pyzil import crypto
from zilpool.pyzil.crypto import bytes_to_int as b2i
from zilpool.pyzil.crypto import hex_str_to_bytes as h2b

from zilpool.pyzil import schnorr

cur_dir = os.path.dirname(os.path.abspath(__file__))


class TestSchnorr:
    def test_vectors(self):
        vectors = json.load(open(os.path.join(cur_dir, "schnorr.fixtures.json")))
        for vector in random.choices(vectors, k=50):
            for key in vector:
                vector[key] = h2b(vector[key])

            sign = schnorr.sign_with_k(
                vector["msg"],
                vector["priv"],
                b2i(vector["k"])
            )
            assert not not sign

            r, s = schnorr.decode_signature(sign)
            assert r == b2i(vector["r"])
            assert s == b2i(vector["s"])

            sign = schnorr.encode_signature(r, s)

            assert schnorr.verify(vector["msg"], sign, vector["pub"])

    def test_sign_verify(self):
        for i in range(10):
            msg = crypto.rand_bytes(1 + i * 512)
            key = crypto.ZilKey.generate_key_pair()

            signature1 = schnorr.sign(msg, key.keypair_bytes.private)
            signature2 = schnorr.sign(msg, key.keypair_bytes.private)

            assert signature1 != signature2
            assert schnorr.verify(msg, signature1, key.keypair_bytes.public)
            assert schnorr.verify(msg, signature2, key.keypair_bytes.public)

    def test_encode_decode(self):
        for i in range(10):
            priv_key = schnorr.gen_private_key()
            pub_key = schnorr.get_public_key(priv_key)

            encoded_pub = schnorr.encode_public(pub_key.x, pub_key.y,
                                                compressed=True)
            decoded_pub = schnorr.decode_public(encoded_pub)

            assert pub_key == decoded_pub

            encoded_pub = schnorr.encode_public(pub_key.x, pub_key.y,
                                                compressed=False)
            decoded_pub = schnorr.decode_public(encoded_pub)

            assert pub_key == decoded_pub
