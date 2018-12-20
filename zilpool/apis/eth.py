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

from typing import List
from jsonrpcserver import method


def init_apis(config):
    @method
    async def eth_getWork() -> List[str]:
        return ["header", "seed", "boundary"]

    @method
    async def eth_submitWork(nonce: str, header: str,
                             mix_digest: str, miner_wallet: str) -> bool:
        assert (len(nonce) == 18 and
                len(header) == 66 and
                len(mix_digest) == 66 and
                len(miner_wallet) == 42)

        return True

    @method
    async def eth_submitHashrate(hashrate: str, miner_id: str) -> bool:
        assert (len(hashrate) == 66 and
                len(miner_id) == 66)
        return True
