# -*- coding: utf-8 -*-
# Zilliqa Mining Pool
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

import os
import json
import random

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
