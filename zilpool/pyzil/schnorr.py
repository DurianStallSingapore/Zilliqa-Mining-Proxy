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

import os
import sys
import secrets
import hashlib
from typing import Optional
from functools import partial

cur_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(cur_dir)

from ecpy import formatters
from ecpy.curves import Curve as ECCurve
from ecpy.curves import Point as ECPoint
from ecpy.ecschnorr import ECSchnorr
from ecpy.keys import ECPublicKey, ECPrivateKey


encode_signature = partial(formatters.encode_sig, fmt="RAW", size=32)
decode_signature = partial(formatters.decode_sig, fmt="RAW")


curve = ECCurve.get_curve("secp256k1")
zil_signer = ECSchnorr(hashlib.sha256, option="Z", fmt="RAW", size=32)


__all__ = [
    "curve", "zil_signer",
    "encode_signature", "decode_signature",
    "ECCurve", "ECPoint", "ECPublicKey", "ECPrivateKey",
    "sign", "sign_with_k", "verify",
]


def sign(bytes_msg: bytes, bytes_private: bytes,
         retries=10) -> Optional[bytes]:

    for i in range(retries):
        k = secrets.randbelow(curve.order)
        if k == 0:
            continue
        signature = sign_with_k(bytes_msg, bytes_private, k)
        if signature:
            return signature
    return None


def sign_with_k(bytes_msg: bytes,
                bytes_private: bytes,
                k: int) -> Optional[bytes]:
    from .crypto import bytes_to_int

    private_key = ECPrivateKey(bytes_to_int(bytes_private), curve)

    return zil_signer.sign_k(bytes_msg, private_key, k)


def verify(bytes_msg: bytes,
           signature: bytes,
           bytes_public: bytes) -> bool:
    from .crypto import decode_public

    x, y = decode_public(bytes_public)

    point = ECPoint(x, y, curve=curve)
    ec_pub_key = ECPublicKey(point)

    return zil_signer.verify(bytes_msg, signature, ec_pub_key)
