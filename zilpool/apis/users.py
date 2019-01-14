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


from jsonrpcserver import method

from zilpool.common import utils
from zilpool.database import miner, zilnode
from zilpool.web import tools


def init_apis(config):
    @method
    async def register_miner(wallet_address: str, email: str, nick_name=""):
        new_miner = miner_register(config, wallet_address, email, nick_name)
        if not new_miner:
            return False
        resp = new_miner.to_mongo()
        resp.pop("_id", None)
        resp["join_date"] = utils.iso_format(resp["join_date"])
        return resp

    @method
    async def register_node(pub_key: str, email: str):
        result = node_register(config, pub_key, email)
        return {
            "result": result
        }


def miner_register(config, wallet_address, email, nick_name=""):
    wallet_address = utils.valid_addr(wallet_address)
    assert wallet_address, "invalid wallet address"

    email = utils.valid_email(email)
    assert email, "invalid email"

    exist = miner.Miner.get(wallet_address=wallet_address)
    assert not exist, "wallet address exists already"

    new_miner = miner.Miner.get_or_create(
        wallet_address, "default_worker",
        nick_name=nick_name, email=email,
    )
    if not new_miner.email_verified:
        ext_data = {
            "miner_address": new_miner.wallet_address,
        }
        # send verification mail to user
        tools.send_email_verification(config, email, "miner", ext_data=ext_data)

    return new_miner


def node_register(config, pub_key: str, email: str):
    email = utils.valid_email(email)
    assert email, "invalid email"

    pub_keys = [key for key in pub_key.split(",")]
    for i in range(len(pub_keys)):
        key = pub_keys[i]
        valid_key = utils.valid_pub_key(key)
        if not valid_key:
            raise Exception(f"invalid public key {key}")
        pub_keys[i] = valid_key

    if not pub_keys:
        raise Exception("no public key")

    # 1. get or create node owner
    owner = zilnode.ZilNodeOwner.get_one(email=email)
    if not owner:
        owner = zilnode.ZilNodeOwner.create(email=email)
        owner = owner.save()

    if not owner:
        raise Exception("failed to create node owner")

    if not owner.email_verified:
        # 1.1 send verification mail to user
        tools.send_email_verification(config, email, "owner")

    # 2. register public keys
    for key in pub_keys:
        exist = zilnode.ZilNode.get_by_pub_key(key, authorized=None)
        if exist:
            raise Exception(f"public key exists already, {key}")

    for key in pub_keys:
        owner.register_node(key)

    # 3. send auth required mail to admin
    tools.send_approve_require_email(config, email, pub_keys)

    return True
