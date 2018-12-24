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

import logging
from datetime import datetime, timedelta

import mongoengine as mg
from mongoengine import Q

from .basemodel import ModelMixin


class PowWork(ModelMixin, mg.Document):
    header = mg.StringField(max_length=128, required=True)
    seed = mg.StringField(max_length=128, required=True)
    boundary = mg.StringField(max_length=128, required=True)
    pub_key = mg.StringField(max_length=128)
    signature = mg.StringField(max_length=128)

    start_time = mg.DateTimeField(default=datetime.utcnow)
    expire_time = mg.DateTimeField()

    finished = mg.BooleanField(default=False)

    miner_wallet = mg.StringField(max_length=128)
    pow_fee = mg.FloatField(default=0.0)
    dispatched = mg.IntField(default=0)

    meta = {"collection": "zil_pow_works"}

    @classmethod
    def new_work(cls, header: str, seed: str, boundary: str,
                 pub_key="", signature="", timeout=120):
        start_time = datetime.utcnow()
        expire_time = start_time + timedelta(seconds=timeout)

        return cls(header=header, seed=seed, boundary=boundary,
                   pub_key=pub_key, signature=signature,
                   start_time=start_time, expire_time=expire_time)

    @classmethod
    def get_new_works(cls, count=1, min_fee=0.0, max_dispatch=None):
        query = Q(finished=False) & Q(pow_fee__gte=min_fee) & Q(expire_time__gte=datetime.utcnow())
        if max_dispatch is not None:
            query = query & Q(dispatched__lt=max_dispatch)

        cursor = cls.objects(query).order_by("-pow_fee", "expire_time", "dispatched")
        works = cursor.limit(count).all()
        if count == 1:
            return works[0] if works else None
        return works

    @classmethod
    def find_work_by_header_boundary(cls, header: str, boundary: str):
        query = Q(finished=False) & Q(header=header) & Q(boundary=boundary) & \
                Q(expire_time__gte=datetime.utcnow())
        cursor = cls.objects(query).order_by("expire_time")
        return cursor.first()

    def verify_signature(self)->bool:
        return True

    def increase_dispatched(self, count=1, inc_expire_seconds=1):
        if inc_expire_seconds > 0:
            new_expire_time = self.expire_time + timedelta(seconds=inc_expire_seconds)
            res = self.update(inc__dispatched=count, set__expire_time=new_expire_time)
        else:
            res = self.update(inc__dispatched=count)

        if res is None:
            return None
        self.reload()
        return self


class PowResult(ModelMixin, mg.Document):
    meta = {"collection": "zil_pow_results"}

    header = mg.StringField(max_length=128, required=True)
    seed = mg.StringField(max_length=128, required=True)
    boundary = mg.StringField(max_length=128, required=True)
    pub_key = mg.StringField(max_length=128, required=True)

    mix_digest = mg.StringField(max_length=128, required=True)
    nonce = mg.StringField(max_length=128, required=True)

    finished_time = mg.DateTimeField(default=datetime.utcnow)
    verified_time = mg.DateTimeField()

    verified = mg.BooleanField(default=False)
    miner_wallet = mg.StringField(max_length=128)
    worker_name = mg.StringField(max_length=64, default="")
