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
from datetime import datetime
from jsonrpcserver import method

from zilpool.common import utils
from zilpool.pyzil import crypto
from zilpool.database import pow, zilnode


def init_apis(config):
    zil_config = config["api_server"]["zil"]

    @method
    @utils.args_to_lower
    async def zil_requestWork(pub_key: str, header: str,
                              block_num: str, boundary: str,
                              timeout: str, signature: str) -> bool:
        assert (len(pub_key) == 68 and      # 33 bytes -> "0x" + 66 chars
                len(header) == 66 and       # 32 bytes -> "0x" + 64 chars
                len(block_num) == 18 and    # 8 bytes  -> "0x" + 16 chars
                len(boundary) == 66 and     # 32 bytes -> "0x" + 64 chars
                len(timeout) == 10 and      # 4 bytes  -> "0x" + 8 chars
                len(signature) == 130)      # 64 bytes -> "0x" + 128 chars

        # verify signature
        if not verify_signature(pub_key, signature,
                                pub_key, header, block_num, boundary, timeout):
            logging.warning(f"failed verify signature")
            return False

        block_num = crypto.hex_str_to_int(block_num)
        timeout = crypto.hex_str_to_int(timeout)

        node = zilnode.ZilNode.get_by_pub_key(pub_key=pub_key, authorized=True)
        if not (node and node.authorized):
            logging.warning(f"unauthorized public key: {pub_key}")
            return False

        work = pow.PowWork.new_work(header, block_num, boundary,
                                    pub_key=pub_key, signature=signature,
                                    timeout=timeout)

        work = work.save()
        return work is not None

    work_not_done = (False, "", "", "")

    @method
    @utils.args_to_lower
    async def zil_checkWorkStatus(pub_key: str, header: str,
                                  boundary: str, signature: str) -> [list, tuple]:
        assert (len(pub_key) == 68 and
                len(header) == 66 and
                len(boundary) == 66 and
                len(signature) == 130)    # 64 bytes -> 128 chars + "0x"

        # verify signature
        if not verify_signature(pub_key, signature,
                                pub_key, header, boundary):
            logging.warning(f"failed verify signature")
            return False

        pow_result = pow.PowResult.get_pow_result(header, boundary, pub_key=pub_key)

        if not pow_result:
            logging.warning(f"result not found for pub_key: {pub_key}, "
                            f"header: {header}, boundary: {boundary}")
            return work_not_done

        return True, pow_result.nonce, pow_result.header, pow_result.mix_digest

    @method
    @utils.args_to_lower
    async def zil_verifyResult(pub_key: str, verified: str,
                               header: str, boundary: str, signature: str) -> bool:
        assert (len(pub_key) == 68 and
                len(verified) == 4 and
                len(header) == 66 and
                len(boundary) == 66 and
                len(signature) == 130)    # 64 bytes -> "0x" + 128 chars

        # verify signature
        if not verify_signature(pub_key, signature,
                                pub_key, verified, header, boundary):
            logging.warning(f"failed verify signature")
            return False

        pow_result = pow.PowResult.get_pow_result(header, boundary, pub_key=pub_key)

        if not pow_result:
            logging.warning(f"result not found for pub_key: {pub_key}, "
                            f"header: {header}, boundary: {boundary}")
            return False

        verified = verified == "0x01"
        if pow_result.update(verified=verified,
                             verified_time=datetime.utcnow()):
            worker = pow_result.get_worker()
            if not worker:
                logging.warning(f"worker not found, {pow_result.worker_name}"
                                f"@{pow_result.miner_wallet}")
            else:
                worker.update_stat(inc_verified=1)

            return True

        logging.warning(f"Failed update pow result {pow_result}")
        return False

    def verify_signature(pub_key, signature, *parameters):
        if zil_config["verify_sign"] is False:
            return True

        key = crypto.ZilKey(str_public=pub_key)

        msg_to_verify = b""
        for param in parameters:
            if isinstance(param, bytes):
                b_param = param
            elif isinstance(param, str):
                b_param = crypto.hex_str_to_bytes(param)
            elif isinstance(param, bool):
                b_param = b"\x01" if param else b"\x00"
            elif isinstance(param, int):
                b_param = crypto.int_to_bytes(param, n_bytes=8)
            else:
                logging.warning(f"wrong data type")
                return False

            msg_to_verify += b_param

        return key.verify(signature, msg_to_verify)
