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

from zilpool.database import init_db
from zilpool.database.basemodel import db, drop_all
from zilpool.tests.test_config import get_database_debug_config
from zilpool.pyzil.crypto import rand_hex_str, ZilKey


class TestDatabase:
    init_db(get_database_debug_config())

    def test_init(self):
        result = db.command("ping")
        assert result["ok"]

    def test_zil_nodes(self):
        from zilpool.database.zilnode import ZilNode

        drop_all()

        def check_doc_count(i):
            assert ZilNode._collection.count_documents({}) == i

        key = ZilKey.generate_key_pair()
        pub_key = key.keypair_str.public
        node = ZilNode(pub_key=pub_key, pow_fee=0, authorized=False)
        node.save()
        check_doc_count(1)
        node.update(set__pow_fee=1.2)
        check_doc_count(1)
        node2 = ZilNode.get_by_pub_key(pub_key, authorized=False)
        assert node2.pow_fee == node.pow_fee == 1.2

        node = ZilNode.get_by_pub_key("")
        assert node is None
        node = ZilNode(pub_key=pub_key)
        success = node.save()
        assert not success
        check_doc_count(1)

        fail_pub_key = rand_hex_str(9)
        node2 = ZilNode(pub_key=fail_pub_key, pow_fee=6, authorized=True)
        check_doc_count(1)
        success = node2.save()
        assert success is node2
        check_doc_count(2)
        success = node2.save()
        assert success is node2
        check_doc_count(2)

        drop_all()

    def test_pow_work(self):
        from zilpool.database.pow import PowWork

        def check_doc_count(i):
            assert PowWork._collection.count_documents({}) == i

        drop_all()

        header = rand_hex_str(64, prefix="0x")
        seed = rand_hex_str(64, prefix="0x")
        boundary = rand_hex_str(64, prefix="0x")
        pub_key = ZilKey.generate_key_pair().keypair_str.public

        work = PowWork.new_work(header, seed, boundary, pub_key=pub_key)
        work.pow_fee = 2
        work.save()
        check_doc_count(1)
        assert not work.finished

        work = PowWork.get_new_works(1, min_fee=2.01)
        assert not work

        work = PowWork.get_new_works(1, min_fee=2.0)
        assert work
        assert work.dispatched == 0

        work = work.increase_dispatched()
        assert work

        work = PowWork.find_work_by_header_boundary(header=header, boundary=boundary)
        assert work
        assert work.dispatched == 1

        work2 = PowWork.get_new_works(1, min_fee=0)
        assert work2.header == work.header, work2.boundary == work.boundary

        drop_all()
