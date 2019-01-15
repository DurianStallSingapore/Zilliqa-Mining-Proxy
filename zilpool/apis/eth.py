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
    default_miner = config.mining.get(
        "default_miner", "0x0123456789012345678901234567890123456789"
    )

    def no_work():
        seconds_to_next_pow = pow.PowWork.calc_seconds_to_next_pow()
        return "", "", "", False, int(seconds_to_next_pow)

    @method
    @utils.args_to_lower
    async def eth_getWork() -> [List, Tuple]:
        min_fee = config.mining.get("min_fee", 0.0)
        max_dispatch = config.mining.get("max_dispatch", 10)
        inc_expire = config.mining.get("inc_expire", 0)
        work = pow.PowWork.get_new_works(count=1, min_fee=min_fee,
                                         max_dispatch=max_dispatch)
        if not work:
            return no_work()

        if work.increase_dispatched(inc_expire_seconds=inc_expire):
            return work.header, work.seed, work.boundary, True, 0
        logging.warning(f"increase_dispatched failed, {work}")
        return no_work()

    @method
    @utils.args_to_lower
    async def eth_submitWork(nonce: str, header: str, mix_digest: str,
                             boundary: str="", miner_wallet: str="", worker_name: str="") -> bool:
        assert (len(nonce) == 18 and
                len(header) == 66 and
                len(mix_digest) == 66 and
                len(boundary) in [0, 66] and
                len(miner_wallet) in [0, 42] and
                len(worker_name) < 64)

        if not miner_wallet:
            miner_wallet = default_miner

        # 1. validate user input parameters
        nonce_int = h2i(nonce)
        worker_name = valid_worker_name(worker_name)
        miner_wallet_bytes = h2b(miner_wallet)
        mix_digest_bytes = h2b(mix_digest)

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
        boundary_bytes = h2b(work.boundary)
        block_num = ethash.seed_to_block_num(seed)
        hash_result = ethash.verify_pow_work(block_num, header, mix_digest_bytes,
                                             nonce_int, boundary_bytes)
        if not hash_result:
            logging.warning(f"wrong result from miner {miner_wallet}-{worker_name}, {work}")
            _worker.update_stat(inc_failed=1)
            return False

        # 5. check the result if lesser than old one
        if work.finished:
            prev_result = pow.PowResult.get_pow_result(work.header, work.boundary)
            if prev_result:
                if prev_result.verified:
                    logging.warning(f"submitted too late, work is verified. {work.header} {work.boundary}")
                    _worker.update_stat(inc_failed=1)
                    return False

                if ethash.is_less_or_equal(prev_result.hash_result, hash_result):
                    logging.warning(f"submitted result > old result, ignored. {work.header} {work.boundary}")
                    _worker.update_stat(inc_failed=1)
                    return False

        # 6. save to database
        hash_result_str = b2h(hash_result, prefix="0x")
        if not work.save_result(nonce, mix_digest, hash_result_str, miner_wallet, worker_name):
            logging.warning(f"failed to save result for miner "
                            f"{miner_wallet}-{worker_name}, {work}")
            return False

        _worker.update_stat(inc_finished=1)

        # 6. todo: miner reward
        return True

    @method
    @utils.args_to_lower
    async def eth_submitHashrate(hashrate: str, miner_wallet: str,
                                 worker_name: str="") -> bool:
        hashrate_int, miner_wallet_bytes = h2i(hashrate), h2b(miner_wallet)
        worker_name = valid_worker_name(worker_name)

        hr_record = miner.HashRate.log(hashrate_int, miner_wallet, worker_name)
        if not hr_record:
            return False

        return True

    def valid_worker_name(worker_name: str) -> str:
        worker_name = worker_name.strip()
        if not worker_name:
            worker_name = "default_worker"
        assert utils.is_valid_str(worker_name)
        return worker_name
