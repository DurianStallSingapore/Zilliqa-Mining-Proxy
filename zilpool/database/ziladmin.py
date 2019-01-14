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

import json
import logging
import hashlib
from datetime import datetime, timedelta

import mongoengine as mg

from .basemodel import ModelMixin

from zilpool.pyzil import crypto
from zilpool.common.utils import encrypt_password, verify_password


AdminActions = [
    "verify_miner_email",
    "verify_owner_email",
    "approve_nodes",
    "reject_nodes",
]


class ZilAdminToken(ModelMixin, mg.Document):
    meta = {"collection": "zil_admin_token"}

    token = mg.StringField(max_length=128)
    expire_time = mg.DateTimeField()
    finished = mg.BooleanField(default=False)

    action = mg.StringField(max_length=32)
    ext_data = mg.DictField()

    @classmethod
    def calc_hash(cls, ext_data):
        return hashlib.sha256(json.dumps(ext_data).encode()).hexdigest()[:8]

    def check_hash(self, data_hash):
        return self.calc_hash(self.ext_data) == data_hash

    @classmethod
    def create_token(cls, action, ext_data=None, expire_secs=24*60*60):
        assert action in AdminActions

        if ext_data is None:
            ext_data = {}

        data_hash = cls.calc_hash(ext_data)

        token = crypto.rand_string(8) + data_hash
        expire_time = datetime.utcnow() + timedelta(seconds=expire_secs)

        admin_token = cls(token=token, expire_time=expire_time, finished=False,
                          action=action, ext_data=ext_data)
        admin_token = admin_token.save()

        return admin_token and admin_token.token

    @classmethod
    def verify_token(cls, token, action):
        admin_token = cls.get_one(token=token, action=action)
        if not admin_token:
            return None

        if admin_token.finished:
            return None

        if datetime.utcnow() > admin_token.expire_time:
            return None

        ext_hash = token[8:]
        if not admin_token.check_hash(ext_hash):
            return None

        return admin_token

    def set_token_done(self):
        self.finished = True
        if not self.save():
            logging.error("database error, failed to save admin token")

    def do_action(self):
        action_func = getattr(self, self.action)
        if not callable(action_func):
            raise NotImplementedError
        return action_func()

    def verify_miner_email(self):
        from .miner import Miner

        email = self.ext_data["email"]
        wallet_address = self.ext_data["miner_address"]
        _miner = Miner.get_one(email=email, wallet_address=wallet_address)
        if not _miner:
            raise Exception(f"miner {wallet_address} not found")

        if not _miner.email_verified:
            _miner.email_verified = True
            if not _miner.save():
                raise Exception("database error")

        self.set_token_done()

        return True, f"Miner email {email} was verified for wallet {wallet_address}"

    def verify_owner_email(self):
        from .zilnode import ZilNodeOwner

        email = self.ext_data["email"]
        owner = ZilNodeOwner.get_one(email=email)
        if not owner:
            raise Exception("email not found")

        if not owner.email_verified:
            owner.email_verified = True
            if not owner.save():
                raise Exception("database error")

        self.set_token_done()

        return True, f"Node email {email} was verified"

    def authorize_nodes(self, authorized=True):
        from .zilnode import ZilNode
        from zilpool.web.tools import send_auth_notification_email

        user_email = self.ext_data.get("email", "")
        pub_keys = self.ext_data["pub_keys"]
        if not pub_keys:
            raise Exception("no public keys to approve")

        messages = [f"Node Registers from {user_email}"]

        for key in pub_keys:
            node = ZilNode.get_by_pub_key(key, authorized=None)
            if not node:
                messages.append(f"{key}, not found ")
                continue
            if not node.update(authorized=authorized):
                messages.append(f"{key}, database error")
                continue
            res = "approved" if node.authorized else "rejected"
            messages.append(f"{key}, {res}")

        self.set_token_done()
        messages = "\n".join(messages)

        send_auth_notification_email(user_email, messages)

        return True, messages

    def approve_nodes(self):
        return self.authorize_nodes(True)

    def reject_nodes(self):
        return self.authorize_nodes(False)


class ZilAdmin(ModelMixin, mg.Document):
    meta = {"collection": "zil_admin"}
    email = mg.StringField(max_length=128, required=True, unique=True)
    password_hash = mg.StringField(max_length=128, required=True)
    visa = mg.StringField(max_length=128)    # for login api
    visa_expire_time = mg.DateTimeField()

    @classmethod
    def create(cls, email, password):
        password_hash = encrypt_password(password)
        admin = cls(email=email, password_hash=password_hash)
        return admin.save()

    @classmethod
    def login(cls, email, password, expire_secs=30*60):
        admin = cls.get_one(email=email)
        if not admin:
            return None
        if not verify_password(password, admin.password_hash):
            return None
        return admin.create_visa(expire_secs=expire_secs)

    @classmethod
    def logout(cls, email):
        admin = cls.get_one(email=email)
        if not admin:
            return None
        return admin.update(visa="")

    @classmethod
    def check_visa(cls, visa, email=None):
        if email is None:
            admin = cls.get_one(visa=visa)
        else:
            admin = cls.get_one(email=email, visa=visa)
        if not admin or not admin.visa:
            return None
        if datetime.utcnow() > admin.visa_expire_time:
            admin.update(visa="")
            return None
        return admin

    def create_visa(self, expire_secs=30*60):
        visa = crypto.rand_string(8)
        visa_expire_time = datetime.utcnow() + timedelta(seconds=expire_secs)
        if not self.update(visa=visa, visa_expire_time=visa_expire_time):
            return None
        return self
