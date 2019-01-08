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

from zilpool.pyzil import crypto, ethash

from . import miner
from .basemodel import ModelMixin


class PowWork(ModelMixin, mg.Document):
    header = mg.StringField(max_length=128, required=True)
    seed = mg.StringField(max_length=128, required=True)
    boundary = mg.StringField(max_length=128, required=True)
    pub_key = mg.StringField(max_length=128)
    signature = mg.StringField(max_length=256)

    block_num = mg.IntField(default=0)
    start_time = mg.DateTimeField()
    expire_time = mg.DateTimeField()

    finished = mg.BooleanField(default=False)

    miner_wallet = mg.StringField(max_length=128)
    pow_fee = mg.FloatField(default=0.0)
    dispatched = mg.IntField(default=0)

    meta = {"collection": "zil_pow_works"}

    def __str__(self):
        return f"[PowWork: {self.header}, {self.finished}, {self.expire_time}]"

    @classmethod
    def new_work(cls, header: str, block_num: int, boundary: str,
                 pub_key="", signature="", timeout=120):
        start_time = datetime.utcnow()
        expire_time = start_time + timedelta(seconds=timeout)
        seed = ethash.block_num_to_seed(block_num)
        seed = crypto.bytes_to_hex_str_0x(seed)

        return cls(header=header, seed=seed, boundary=boundary,
                   pub_key=pub_key, signature=signature, block_num=block_num,
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
    def find_work_by_header_boundary(cls, header: str, boundary: str,
                                     check_expired=True, order="expire_time"):
        query = Q(header=header) & Q(boundary=boundary)
        if check_expired:
            query = query & Q(expire_time__gte=datetime.utcnow())
        cursor = cls.objects(query).order_by(order)    # default to get the oldest one
        return cursor.first()

    @classmethod
    def get_latest_work(cls):
        return cls.objects().order_by("-expire_time").first()

    @classmethod
    def calc_seconds_to_next_pow(cls):
        # 1. get the latest work order by expire_time
        latest_work = cls.get_latest_work()
        if not latest_work:
            return 0     # no work, return default

        # 2. check expire_time
        now = datetime.utcnow()
        if now <= latest_work.expire_time:
            return 0      # we still within pow window

        # 3. get last work in prev epoch
        cur_block = latest_work.block_num
        prev_block = cur_block - 1
        prev_epoch_work = cls.objects(block_num=prev_block).order_by("-expire_time").first()
        if not prev_epoch_work:
            return 0      # can find work in prev epoch

        epoch_time = latest_work.start_time - prev_epoch_work.expire_time

        # 4. get the first work in this epoch
        first_work_this_epoch = cls.objects(block_num=cur_block).order_by("expire_time").first()
        if first_work_this_epoch:
            epoch_time = first_work_this_epoch.start_time - prev_epoch_work.expire_time

        if epoch_time.total_seconds() <= 0:
            return 0      # epoch time is less than pow window, overlap

        # 5. roughly calc next pow time
        next_pow_time = latest_work.start_time + epoch_time

        if now > next_pow_time:
            return 0      # pow already start but no work received

        return (next_pow_time - now).total_seconds()

    def increase_dispatched(self, count=1, inc_expire_seconds=0):
        if inc_expire_seconds > 0:
            new_expire_time = self.expire_time + timedelta(seconds=inc_expire_seconds)
            res = self.update(inc__dispatched=count, set__expire_time=new_expire_time)
        else:
            res = self.update(inc__dispatched=count)

        if res is None:
            return None
        self.reload()
        return self

    def save_result(self, nonce: str, mix_digest: str, hash_result: str,
                    miner_wallet: str, worker_name: str):
        pow_result = PowResult(header=self.header, seed=self.seed,
                               finished_time=datetime.utcnow(),
                               block_num=self.block_num, hash_result=hash_result,
                               boundary=self.boundary, pub_key=self.pub_key,
                               mix_digest=mix_digest, nonce=nonce, verified=False,
                               miner_wallet=miner_wallet, worker_name=worker_name)
        if pow_result.save():
            res = self.update(set__finished=True, set__miner_wallet=miner_wallet)
            if res:
                return pow_result
        return None


class PowResult(ModelMixin, mg.Document):
    meta = {"collection": "zil_pow_results"}

    header = mg.StringField(max_length=128, required=True)
    seed = mg.StringField(max_length=128, required=True)
    boundary = mg.StringField(max_length=128, required=True)
    pub_key = mg.StringField(max_length=128, required=True)

    mix_digest = mg.StringField(max_length=128, required=True)
    nonce = mg.StringField(max_length=128, required=True)
    hash_result = mg.StringField(max_length=128, required=True)

    block_num = mg.IntField(default=0)
    finished_time = mg.DateTimeField()
    verified_time = mg.DateTimeField()

    verified = mg.BooleanField(default=False)
    miner_wallet = mg.StringField(max_length=128)
    worker_name = mg.StringField(max_length=64, default="")

    def __str__(self):
        return f"[PowResult: {self.pub_key}, {self.header}]"

    @classmethod
    def get_pow_result(cls, header, boundary, pub_key=None, order="-finished_time"):
        query = Q(header=header) & Q(boundary=boundary)
        if pub_key is not None:
            query = query & Q(pub_key=pub_key)
        cursor = cls.objects(query).order_by(order)    # default to get latest one
        return cursor.first()

    def get_worker(self):
        return miner.Worker.get_or_create(self.miner_wallet, self.worker_name)
