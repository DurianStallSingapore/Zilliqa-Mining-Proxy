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

from collections import defaultdict
from datetime import datetime, timedelta

import mongoengine as mg
from mongoengine import Q

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
    email_verified = mg.BooleanField(default=False)
    join_date = mg.DateTimeField()

    def __str__(self):
        return f"[Miner: {self.wallet_address}, {self.authorized}]"

    @classmethod
    def get_or_create(cls, wallet_address: str, worker_name: str,
                      nick_name="", email="", authorized=True):
        worker = Worker.get_or_create(wallet_address, worker_name)
        if worker:
            miner = cls.objects(
                wallet_address=wallet_address
            ).modify(
                upsert=True, new=True,
                set__wallet_address=wallet_address,
                set__authorized=authorized,
                set__nick_name=nick_name,
                set__email=email
            )
            if miner.join_date is None:
                miner.update(join_date=datetime.utcnow())
            return miner
        return None

    @property
    def workers(self):
        return Worker.get_all(wallet_address=self.wallet_address)

    def works_stats(self):
        stats = defaultdict(int)
        for worker in self.workers:
            stats["work_submitted"] += worker.work_submitted
            stats["work_failed"] += worker.work_failed
            stats["work_finished"] += worker.work_finished
            stats["work_verified"] += worker.work_verified

        return stats


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

    @classmethod
    def active_count(cls):
        from . import pow
        two_hours = datetime.utcnow() - timedelta(hours=2)

        match = {
            "finished_time": {
                '$gte': two_hours,
            }
        }
        group = {
            "_id": {"miner_wallet": "$miner_wallet", 
                    "worker_name": "$worker_name",},
        }

        return pow.PowResult.aggregate_count(match, group)

    def update_stat(self, inc_submitted=0, inc_failed=0, inc_finished=0, inc_verified=0):
        update_kwargs = {
            "inc__work_submitted": inc_submitted,
            "inc__work_failed": inc_failed,
            "inc__work_finished": inc_finished,
            "inc__work_verified": inc_verified,
        }
        update_kwargs = {key: value for (key, value) in update_kwargs.items() if value > 0}
        return self.update(**update_kwargs)

    def works_stats(self):
        return {
            "work_submitted": self.work_submitted,
            "work_failed": self.work_failed,
            "work_finished": self.work_finished,
            "work_verified": self.work_verified,
        }


class HashRate(ModelMixin, mg.Document):
    meta = {"collection": "zil_mine_hashrate"}

    wallet_address = mg.StringField(max_length=128, required=True)
    worker_name = mg.StringField(max_length=64, default="")

    hashrate = mg.IntField(default=0.0, required=True)
    updated_time = mg.DateTimeField()

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
                 hashrate=hashrate, updated_time=datetime.utcnow())
        return hr.save()

    @classmethod
    def epoch_hashrate(cls, block_num, wallet_address=None, worker_name=None):
        from .pow import PowWork

        epoch_start, epoch_end = PowWork.calc_epoch_window(block_num)
        if not epoch_start or not epoch_end:
            return -1

        match = {
            "updated_time": {
                "$gte": epoch_start,
                "$lte": epoch_end,
            }
        }

        if wallet_address is not None:
            match.update({
                "wallet_address": {
                    "$eq": wallet_address,
                }
            })

        if worker_name is not None:
            match.update({
                "worker_name": {
                    "$eq": worker_name,
                }
            })

        group = {
            "_id": {"wallet_address": "$wallet_address",
                    "worker_name": "$worker_name", },
            "hashrate": {"$max": "$hashrate"}
        }
        project = {
            "hashrate": {"$sum": "$hashrate"}
        }

        pipeline = [
            {"$match": match},
            {"$group": group},
            {"$project": project}
        ]

        res = list(cls.objects.aggregate(*pipeline))
        return res[0]["hashrate"] if res else 0
