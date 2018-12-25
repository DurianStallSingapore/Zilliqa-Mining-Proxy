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
from typing import List, Tuple
from jsonrpcserver import method

from zilpool.common import utils
from zilpool.database import pow, miner
from zilpool.pyzil import ethash
from zilpool.pyzil.crypto import hex_str_to_bytes as h2b
from zilpool.pyzil.crypto import hex_str_to_int as h2i
from zilpool.pyzil.crypto import bytes_to_hex_str as b2h


def init_apis(config):
    no_work = ("", "", "", False, 10)

    @method
    async def eth_getWork() -> [List, Tuple]:
        min_fee = config.mining["min_fee"]
        max_dispatch = config.mining["max_dispatch"]
        work = pow.PowWork.get_new_works(count=1, min_fee=min_fee,
                                         max_dispatch=max_dispatch)
        if not work:
            return no_work

        if work.increase_dispatched(inc_expire_seconds=5):
            return work.header, work.seed, work.boundary, True, 0
        logging.warning(f"increase_dispatched failed, {work}")
        return no_work

    @method
    async def eth_submitWork(nonce: str, header: str, mix_digest: str,
                             boundary: str, miner_wallet: str,
                             worker_name: str="") -> bool:
        assert (len(nonce) == 18 and
                len(header) == 66 and
                len(mix_digest) == 66 and
                len(boundary) == 66 and
                len(miner_wallet) == 42 and
                len(worker_name) < 64)

        # 1. validate user input parameters
        worker_name = worker_name.strip()
        assert utils.is_valid_str(worker_name)
        worker_name = worker_name if len(worker_name) > 0 else "default_worker"

        nonce_int, mix_digest_bytes, boundary_bytes = h2i(nonce), h2b(mix_digest), h2b(boundary)
        miner_wallet_bytes = h2b(miner_wallet)

        # 2. get or create miner/worker
        _miner = miner.Miner.get_or_create(miner_wallet, worker_name)
        _worker = miner.Worker.get_or_create(miner_wallet, worker_name)
        if not _miner or not _worker:
            logging.warning("miner/worker not found, {worker_name}@{miner_wallet}")
            return False
        _worker.update_stat(inc_submitted=1)

        # 3. check work existing
        work = pow.PowWork.find_work_by_header_boundary(header=header, boundary=boundary,
                                                        check_expired=True)
        if not work:
            logging.warning(f"work not found or expired, {header} {boundary}")
            _worker.update_stat(inc_failed=1)
            return False

        # 4. verify result
        seed, header = h2b(work.seed), h2b(work.header)

        block_num = ethash.seed_to_block_num(seed)
        hash_result = ethash.verify_pow_work(block_num, header, mix_digest_bytes,
                                             nonce_int, boundary_bytes)
        if not hash_result:
            logging.warning(f"wrong result from miner {miner_wallet}-{worker_name}, {work}")
            _worker.update_stat(inc_failed=1)
            return False

        # 5. check the result if lesser than old one
        if work.finished:
            prev_result = pow.PowResult.get_by_header_boundary(work.header, boundary)
            if prev_result and ethash.is_less_or_equal(prev_result.hash_result, hash_result):
                logging.warning(f"submitted result > old result, ignored")
                _worker.update_stat(inc_failed=1)
                return False

        # 6. save to database
        hash_result_str = b2h(hash_result, prefix="0x")
        if not work.save_result(nonce, mix_digest, hash_result_str, miner_wallet, worker_name):
            logging.warning(f"failed to save result for miner {miner_wallet}-{worker_name}, {work}")
            return False

        _worker.update_stat(inc_finished=1)

        # 6. todo: miner reward
        return True

    @method
    async def eth_submitHashrate(hashrate: str, miner_wallet: str, worker_name: str) -> bool:
        assert (len(hashrate) == 66 and
                len(miner_wallet) == 66 and
                len(worker_name) < 64)
        hashrate_int, miner_wallet_bytes = h2i(hashrate), h2b(miner_wallet)
        worker_name = worker_name if len(worker_name) > 0 else "default_worker"
        return True
