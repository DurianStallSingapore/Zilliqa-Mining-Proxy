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

import enum
import logging
from datetime import datetime, timedelta

import mongoengine as mg

from .basemodel import ModelMixin

from zilpool.pyzil import crypto
from zilpool.common.utils import encrypt_password, verify_password


class ZilAdminToken(ModelMixin, mg.Document):
    meta = {"collection": "zil_admin_token"}

    admin_email = mg.StringField(max_length=128, required=True)

    token = mg.StringField(max_length=128)    # for email approve
    expire_time = mg.DateTimeField()

    action = mg.StringField(max_length=32)
    ext_data = mg.StringField(max_length=1024)

    @classmethod
    def create_token(cls, admin_email, action,
                     expire_secs=24*60*60, ext_data=None):
        admin = ZilAdmin.get_one(email=admin_email)
        if not admin:
            logging.warning(f"admin {admin_email} not exists")
            return None

        expire_time = datetime.utcnow() + timedelta(seconds=expire_secs)

        admin_token = cls(admin_email=admin_email,
                          action=action,
                          token=crypto.rand_string(8),
                          expire_time=expire_time,
                          ext_data=ext_data)
        admin_token = admin_token.save()

        return admin_token and admin_token.token

    @classmethod
    def check_token(cls, token, action):
        admin_token = cls.get_one(token=token, action=action)
        if not admin_token:
            return None
        if datetime.utcnow() > admin_token.expire_time:
            admin_token.delete()
            return None
        return admin_token


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
