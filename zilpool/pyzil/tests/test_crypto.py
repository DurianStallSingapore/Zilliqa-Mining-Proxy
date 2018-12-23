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

import pytest

from zilpool.pyzil import crypto


def path_join(*path):
    import os
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(cur_dir, *path)


class TestCrypto:
    def test_rand(self):
        assert isinstance(crypto.rand_bytes(12), bytes)
        assert isinstance(crypto.rand_hex_str(12), str)

        assert crypto.rand_bytes(1) != crypto.rand_bytes(1)
        assert len(crypto.rand_bytes(11)) == 11
        assert len(crypto.rand_bytes(999)) == 999

        for i in range(-99, 1):
            with pytest.raises(ValueError):
                crypto.rand_bytes(i)

        assert crypto.rand_hex_str(2) != crypto.rand_hex_str(2)
        assert len(crypto.rand_hex_str(11)) == 11
        assert len(crypto.rand_hex_str(999)) == 999
        assert len(crypto.rand_hex_str(1000)) == 1000
        assert len(crypto.rand_hex_str(999, prefix="0x")) == 999 + 2

        for i in range(-99, 1):
            with pytest.raises(ValueError):
                crypto.rand_hex_str(i)

    def test_hex_str(self):
        hex_str = "DEADBEEF"
        hex_str_odd = "deadbee"
        bin_bytes = b"\xde\xad\xbe\xef"
        bin_bytes_odd = b"\x0d\xea\xdb\xee"

        assert crypto.hex_str_to_bytes(hex_str) == bin_bytes
        assert crypto.bytes_to_hex_str(bin_bytes) == hex_str.lower()

        assert crypto.hex_str_to_int(hex_str) == 0xDEADBEEF
        assert crypto.bytes_to_int(bin_bytes) == 0xdeadbeef

        assert crypto.hex_str_to_int(hex_str_odd) == 0xDEADBEE
        assert crypto.bytes_to_int(bin_bytes_odd) == 0xDEADBEE

    def test_hex_str_padding(self):
        dead_beef = 0xDEADBEEF

        assert len(crypto.int_to_bytes(dead_beef)) == crypto.TOKEN_NUM_BYTES
        assert crypto.int_to_bytes(dead_beef, n_bytes=None) == b"\xde\xad\xbe\xef"

        for i in range(4):
            with pytest.raises(OverflowError, message="Expecting OverflowError:"):
                crypto.int_to_bytes(dead_beef, n_bytes=i)

        for i in range(5, 130):
            assert len(crypto.int_to_bytes(dead_beef, n_bytes=i)) == i

    def test_zil_mykey(self):
        key = crypto.ZilKey.load_mykey_txt(path_join("mykey.txt"))
        assert key.address == "967e40168af66f441b73c0146e26069bfc3accc7"

        with pytest.raises(AssertionError):
            crypto.ZilKey("02A349FA10F0E6A614A38D6033588A422357F2C60AF2EEBAE15D06498DF8AF0B05",
                          "75889EA1AF5D402B69E61C654C74D8B569E363D2E271E1E6E2B63FDB9B635173")

        new_key = crypto.ZilKey(
            "02A349FA10F0E6A614A38D6033588A422357F2C60AF2EEBAE15D06498DF8AF0B05",
            "75889EA1AF5D402B69E61C654C74D8B569E363D2E271E1E6E2B63FDB9B635174"
        )

        assert key == new_key
        assert key != crypto.ZilKey.generate_key_pair()
