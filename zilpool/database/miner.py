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

from datetime import datetime

import mongoengine as mg

from .basemodel import ModelMixin


"""
A Miner -> Many Workers
A Worker -> Time series of hashrate
"""


class Miner(ModelMixin, mg.Document):
    meta = {"collection": "zil_miners"}

    wallet_address = mg.StringField(max_length=128, required=True, unique=True)
    rewards = mg.FloatField(default=0.0)
    paid = mg.FloatField(default=0.0)
    authorized = mg.BooleanField(default=True)

    nick_name = mg.StringField(max_length=64, default="")
    email = mg.StringField(max_length=128)
    join_date = mg.DateTimeField(default=datetime.utcnow)
    last_updated = mg.DateTimeField(default=datetime.utcnow)

    def __str__(self):
        return f"[Miner: {self.wallet_address}, {self.authorized}]"

    @classmethod
    def get_or_create(cls, wallet_address: str, worker_name: str):
        worker = Worker.get_or_create(wallet_address, worker_name)
        if worker:
            miner = cls.objects(
                wallet_address=wallet_address
            ).modify(
                upsert=True, new=True,
                set__wallet_address=wallet_address
            )
            return miner
        return None


class Worker(ModelMixin, mg.Document):
    meta = {"collection": "zil_mine_workers"}

    wallet_address = mg.StringField(max_length=128, required=True)
    worker_name = mg.StringField(max_length=64, default="")

    work_submitted = mg.IntField(default=0)
    work_failed = mg.IntField(default=0)
    work_finished = mg.IntField(default=0)
    work_verified = mg.IntField(default=0)

    def __str__(self):
        return f"[Worker: {self.worker_name}.{self.wallet_address}]"

    @classmethod
    def get_or_create(cls, wallet_address: str, worker_name: str):
        worker = cls.objects(
            wallet_address=wallet_address,
            worker_name=worker_name
        ).modify(
            upsert=True, new=True,
            set__wallet_address=wallet_address,
            set__worker_name=worker_name
        )
        return worker

    def update_stat(self, inc_submitted=0, inc_failed=0, inc_finished=0, inc_verified=0):
        update_kwargs = {
            "inc__work_submitted": inc_submitted,
            "inc__work_failed": inc_failed,
            "inc__work_finished": inc_finished,
            "inc__work_verified": inc_verified,
        }
        update_kwargs = {key: value for (key, value) in update_kwargs.items() if value > 0}
        return self.update(**update_kwargs)


class HashRate(ModelMixin, mg.Document):
    meta = {"collection": "zil_mine_hashrate"}

    wallet_address = mg.StringField(max_length=128, required=True)
    worker_name = mg.StringField(max_length=64, default="")

    hashrate = mg.IntField(default=0.0, required=True)
    updated_time = mg.DateTimeField(default=datetime.utcnow)

    @classmethod
    def log(cls, hashrate: int, wallet_address: str, worker_name: str):
        if hashrate < 0:
            return False
        _miner = Miner.get(wallet_address=wallet_address)
        if not _miner:
            return False
        _worker = Worker.get_or_create(wallet_address, worker_name)
        if not _worker:
            return False

        hr = cls(wallet_address=wallet_address, worker_name=worker_name,
                 hashrate=hashrate)
        return hr.save()
