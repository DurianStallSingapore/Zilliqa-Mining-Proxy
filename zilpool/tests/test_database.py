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
import random

from zilpool.database import init_db, connect_to_db
from zilpool.database.basemodel import db, drop_all
from zilpool.tests.test_config import get_database_debug_config
from zilpool.pyzil.crypto import rand_hex_str, ZilKey


class TestDatabase:
    connect_to_db(get_database_debug_config())

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
        # seed = rand_hex_str(64, prefix="0x")
        block_num = random.randint(0, 1_000_0000)
        boundary = rand_hex_str(64, prefix="0x")
        pub_key = ZilKey.generate_key_pair().keypair_str.public

        work = PowWork.new_work(header, block_num, boundary, pub_key=pub_key)
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

    def test_node_owner(self):
        import time
        from datetime import datetime
        from zilpool.database.zilnode import ZilNode, ZilNodeOwner

        drop_all()

        email = "test@test.com"
        owner = ZilNodeOwner.create(email)
        assert owner is not None
        assert owner.email_verified is False
        assert owner.pow_fee == 0.0
        assert owner.balance == 0.0
        assert owner.join_date <= datetime.utcnow()

        key = ZilKey.generate_key_pair()
        pub_key = key.keypair_str.public

        node = owner.register_node(pub_key)
        assert pub_key in owner.pending_nodes

        node = ZilNode.get_by_pub_key(pub_key=pub_key, authorized=False)
        assert node is not None
        assert node.authorized is False

        assert node.pow_fee == owner.pow_fee

    def test_admin(self):
        import time
        from zilpool.database.zilnode import ZilNodeOwner
        from zilpool.database.ziladmin import ZilAdminToken

        config = get_database_debug_config()
        drop_all()
        init_db(config)

        action = "verify_owner_email"
        email = "test@test.com"

        ZilNodeOwner.create(email=email)

        token = ZilAdminToken.create_token(action, ext_data={"email": email})
        assert token
        admin_token = ZilAdminToken.verify_token(token, action)
        assert admin_token
        assert admin_token.ext_data["email"] == email

        owner = ZilNodeOwner.get_one(email=email)
        assert owner

        assert not owner.email_verified
        admin_token.do_action()
        owner.reload()
        assert owner.email_verified

        token = ZilAdminToken.create_token(action, ext_data=None, expire_secs=0.1)
        token2 = ZilAdminToken.create_token(action, ext_data=None, expire_secs=1.5)
        assert token
        assert token2
        assert token != token2
        time.sleep(1)
        admin_token = ZilAdminToken.verify_token(token, action)
        admin_token2 = ZilAdminToken.verify_token(token2, action)
        assert admin_token is None
        assert admin_token2 is not None

    def test_site_settings(self):
        from datetime import datetime
        from zilpool.database.ziladmin import SiteSettings

        config = get_database_debug_config()
        drop_all()
        init_db(config)

        drop_all()

        setting0 = SiteSettings.get_setting()
        assert setting0 is None

        setting = SiteSettings.update_setting(
            "admin", min_fee=1.2, max_dispatch=300, inc_expire=1.5,
            notification="notify"
        )
        assert setting is not None
        assert setting.min_fee == 1.2
        assert setting.max_dispatch == 300
        assert setting.inc_expire == 1.5
        assert setting.notification == "notify"
        assert setting.created <= datetime.now()
        assert setting.admin == "admin"

        setting2 = SiteSettings.get_setting()
        assert setting2 == setting

        setting3 = SiteSettings.update_setting(
            admin="new admin", notification="notify 22"
        )
        assert setting3 is not None
        assert setting3 != setting
        assert setting3.min_fee == 1.2
        assert setting3.max_dispatch == 300
        assert setting3.inc_expire == 1.5
        assert setting3.notification == "notify 22"
        assert setting3.created <= datetime.now()
        assert setting3.admin == "new admin"

    def save_result(self, block_num, pow_fee, miner_wallet, worker_name):
        from zilpool.database.pow import PowResult
        pow_result = PowResult(
            header="header", seed="seed", boundary="boundary",
            pub_key="pub_key", mix_digest="mix_digest", nonce="nonce",
            hash_result="hash_result",
            block_num=block_num,
            pow_fee=pow_fee,
            verified=False,
            miner_wallet=miner_wallet,
            worker_name=worker_name
        )
        return pow_result.save()

    def test_stats_reward(self):
        from zilpool.database.pow import PowResult

        config = get_database_debug_config()
        drop_all()
        init_db(config)

        totol_rewards = []
        for i in range(10):
            self.save_result(i, i, "miner1", "worker1")
            self.save_result(i, i * 2 + 10, "miner1", "worker2")
            self.save_result(i, i * 5, "miner2", "worker1")
            totol_rewards.append(i + i * 2 + 10 + i * 5)

        rewards = PowResult.epoch_rewards()
        assert rewards["count"] == 30
        assert rewards["rewards"] == sum(totol_rewards)

        rewards = PowResult.epoch_rewards(miner_wallet="miner1")
        assert rewards["count"] == 20
        assert rewards["rewards"] == sum(totol_rewards) - sum([i * 5 for i in range(10)])

        rewards = PowResult.epoch_rewards(miner_wallet="miner1", worker_name="worker1")
        assert rewards["count"] == 10
        assert rewards["rewards"] == sum(range(10))

        for i in range(10):
            rewards = PowResult.epoch_rewards(block_num=i)
            assert rewards["count"] == 3
            assert rewards["rewards"] == totol_rewards[i]

        rewards = PowResult.epoch_rewards(block_num=(0, 4))
        assert rewards["count"] == 3 * 5
        assert rewards["rewards"] == sum(totol_rewards[0:5])

        rewards = PowResult.epoch_rewards(block_num=9,
                                          miner_wallet="miner1")
        assert rewards["count"] == 2
        assert rewards["rewards"] == totol_rewards[9] - 45

        rewards = PowResult.epoch_rewards(block_num=9,
                                          miner_wallet="miner2")
        assert rewards["count"] == 1
        assert rewards["rewards"] == 45

        rewards = PowResult.epoch_rewards(block_num=9,
                                          miner_wallet="miner1",
                                          worker_name="worker2")
        assert rewards["count"] == 1
        assert rewards["rewards"] == 28
