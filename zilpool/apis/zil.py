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

from jsonrpcserver import method


def init_apis(config):

    @method
    async def zil_requestWork(pub_key: str, header: str,
                              seed: str, boundary: str,
                              timeout: int, signature: str) -> bool:
        assert (len(pub_key) == 68 and
                len(header) == 66 and
                len(seed) == 66 and
                len(boundary) == 66 and
                timeout > 0 and
                len(signature) == 66)
        return True

    @method
    async def zil_checkWorkStatus(pub_key: str, header: str,
                                  boundary: str, signature: str) -> list:
        assert (len(pub_key) == 68 and
                len(header) == 66 and
                len(boundary) == 66 and
                len(signature) == 66)
        return [True, "nonce", "header", "mix digest"]

    @method
    async def zil_verifyResult(pub_key: str, verified: bool,
                               header: str, boundary: str, signature: str) -> bool:
        assert (len(pub_key) == 68 and
                isinstance(verified, bool) and
                len(header) == 66 and
                len(boundary) == 66 and
                len(signature) == 66)
        return True
