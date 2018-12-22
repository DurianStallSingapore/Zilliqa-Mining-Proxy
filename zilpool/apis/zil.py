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

import logging
from jsonrpcserver import method

from ..database import pow, zilnode


def init_apis(config):
    work_not_done = (False, "", "", "")

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

        node = zilnode.ZilNode.get_by_pub_key(pub_key=pub_key, authorized=True)
        if not (node and node.authorized):
            logging.warning(f"unauthorized public key: {pub_key}")
            return False

        work = pow.PowWork.new_work(header, seed, boundary,
                                    pub_key=pub_key, signature=signature,
                                    timeout=timeout)
        if not work.verify_signature():
            logging.warning(f"wrong signature: {work}")
            return False

        work = work.save()
        return work is not None

    @method
    async def zil_checkWorkStatus(pub_key: str, header: str,
                                  boundary: str, signature: str) -> [list, tuple]:
        assert (len(pub_key) == 68 and
                len(header) == 66 and
                len(boundary) == 66 and
                len(signature) == 66)
        return True, "nonce", "header", "mix digest"

    @method
    async def zil_verifyResult(pub_key: str, verified: bool,
                               header: str, boundary: str, signature: str) -> bool:
        assert (len(pub_key) == 68 and
                isinstance(verified, bool) and
                len(header) == 66 and
                len(boundary) == 66 and
                len(signature) == 66)
        return True
