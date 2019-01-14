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

import pytest

from zilpool.pyzil import crypto
from zilpool.pyzil import ethash


class TestEthash:
    def test_tools(self):
        for i in range(256):
            assert ethash.boundary_to_difficulty(ethash.difficulty_to_boundary(i)) == i

    def test_pow(self):
        block_num = 22
        header = crypto.hex_str_to_bytes("372eca2454ead349c3df0ab5d00b0b706b23e49d469387db91811cee0358fc6d")
        excepted_result = crypto.hex_str_to_bytes("00000b184f1fdd88bfd94c86c39e65db0c36144d5e43f745f722196e730cb614")
        excepted_mix = b'/t\xcd\xeb\x19\x8a\xf0\xb9\xab\xe6]"\xd3r\xe2/\xb2\xd4t7\x17t\xa9X<\x1c\xc4\'\xa0y9\xf5'

        nonce = 0x495732e0ed7a801c
        boundary20 = ethash.difficulty_to_boundary(20)
        boundary21 = ethash.difficulty_to_boundary(21)

        calc_mix_digest, calc_result = ethash.pow_hash(block_num, header, nonce)

        assert calc_result == excepted_result
        assert calc_mix_digest == excepted_mix

        assert ethash.verify_pow_work(block_num, header, excepted_mix, nonce, boundary20)
        assert not ethash.verify_pow_work(block_num, header, excepted_mix, nonce, boundary21)

        assert ethash.verify_pow_work(0, header, excepted_mix, nonce, boundary20)
        assert ethash.verify_pow_work(29999, header, excepted_mix, nonce, boundary20)
        assert not ethash.verify_pow_work(30000, header, excepted_mix, nonce, boundary20)
        assert not ethash.verify_pow_work(30001, header, excepted_mix, nonce, boundary20)



