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

import logging
from datetime import datetime, timedelta

import mongoengine as mg
from mongoengine import Q

from zilpool.pyzil import crypto, ethash

from . import miner
from .basemodel import ModelMixin


class PoWWindow(ModelMixin, mg.Document):
    meta = {"collection": "zil_pow_windows"}

    create_time = mg.DateTimeField()
    block_num = mg.IntField(required=True)
    estimated_next_pow = mg.DateTimeField()

    pow_start = mg.DateTimeField(default=datetime.utcnow)
    pow_end = mg.DateTimeField(default=datetime.utcnow)
    pow_window = mg.FloatField(default=0)
    epoch_window = mg.FloatField(default=0)

    @classmethod
    def get_latest_record(cls):
        return cls.objects().order_by("-create_time").first()

    @classmethod
    def get_latest_block_num(cls):
        latest_record = cls.get_latest_record()
        if not latest_record:
            return -1
        return latest_record.block_num

    @classmethod
    def get_pow_window(cls, block_num=None):
        record = cls.objects(block_num=block_num).order_by("-create_time").first()
        if not record:
            return PowWork.calc_pow_window(block_num)
        return record.pow_start, record.pow_end

    @classmethod
    def avg_pow_time(cls, number_blocks=10):
        """ calc pow window from prev records """
        query = cls.objects().order_by("-create_time")
        records = query.limit(number_blocks).all()
        pow_window_list = [r.pow_window for r in records if r.pow_window > 0]
        pow_window_list = sorted(pow_window_list)
        if len(pow_window_list) > 4:
            pow_window_list = pow_window_list[1:-1]

        pow_in_secs = 0
        if len(pow_window_list) > 0:
            pow_in_secs = sum(pow_window_list) / len(pow_window_list)
        return pow_in_secs

    @classmethod
    def avg_epoch_time(cls, number_blocks=10):
        """ calc epoch window( pow included ) from prev records """
        query = cls.objects().order_by("-create_time")
        records = query.limit(number_blocks).all()
        epoch_window_list = [r.epoch_window for r in records if r.epoch_window > 0]
        epoch_window_list = sorted(epoch_window_list)
        if len(epoch_window_list) > 4:
            epoch_window_list = epoch_window_list[1:-1]

        epoch_in_secs = 0
        if len(epoch_window_list) > 0:
            epoch_in_secs = sum(epoch_window_list) / len(epoch_window_list)
        return epoch_in_secs
    
    @classmethod
    def min_epoch_time(cls, number_blocks=10):
        """ calc epoch window( pow included ) from prev records """
        query = cls.objects().order_by("-create_time")
        records = query.limit(number_blocks).all()
        epoch_window_list = [r.epoch_window for r in records if r.epoch_window > 0]
        epoch_window_list = sorted(epoch_window_list)
        if len(epoch_window_list) > 0:
            return epoch_window_list[0]
        return 0        

    @classmethod
    def seconds_to_next_pow(cls):
        last_record = cls.get_latest_record()
        if not last_record or not last_record.estimated_next_pow:
            return 0

        now = datetime.utcnow()
        next_pow_time = last_record.estimated_next_pow
        if now > next_pow_time:
            logging.warning("we are missing some pow_window records")
            return 0

        return (next_pow_time - now).total_seconds()

    @classmethod
    def update_pow_window(cls, work):
        if not work:
            return

        last_record_num = -1
        last_record = cls.get_latest_record()
        if last_record:
            last_record_num = last_record.block_num

        if work.block_num < last_record_num:
            logging.critical("old record found in zil_pow_windows, "
                             "pls clean the database")
            return

        if work.block_num == last_record_num:
            # pow is ongoing, do nothing
            return

        if work.block_num == last_record_num + 1:
            # new epoch start
            # 1. update prev record
            if last_record:
                pow_start, pow_end = PowWork.calc_pow_window(last_record_num)
                if pow_start and pow_end:
                    pow_window = (pow_end - pow_start).total_seconds()
                    epoch_window = (work.start_time - pow_start).total_seconds()

                    last_record.update(
                        pow_start=pow_start,
                        pow_end=pow_end,
                        pow_window=pow_window,
                        epoch_window=epoch_window
                    )

        # 2. create new record and estimate next pow
        epoch_delta = timedelta(seconds=cls.min_epoch_time())
        estimated_next_pow = work.start_time + epoch_delta
        new_record = cls.create(
            block_num=work.block_num,
            create_time=datetime.utcnow(),
            pow_start=work.start_time,
            estimated_next_pow=estimated_next_pow,
        )
        return new_record


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

        return cls.create(
            header=header, seed=seed, boundary=boundary,
            pub_key=pub_key, signature=signature, block_num=block_num,
            start_time=start_time, expire_time=expire_time
        )

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
    def find_work_by_header_boundary(cls, header: str, boundary="",
                                     check_expired=True, order="expire_time"):
        query = Q(header=header)
        if boundary:
            query = query & Q(boundary=boundary)
        if check_expired:
            query = query & Q(expire_time__gte=datetime.utcnow())
        cursor = cls.objects(query).order_by(order)    # default to get the oldest one
        return cursor.first()

    @classmethod
    def get_latest_block_num(cls):
        latest_work = cls.get_latest_work()
        return latest_work.block_num if latest_work else -1

    @classmethod
    def get_first_block_num(cls):
        first_work = cls.get_latest_work(order="start_time")
        return first_work.block_num if first_work else -1

    @classmethod
    def get_latest_work(cls, block_num=None, order="-expire_time"):
        if block_num is None:
            cursor = cls.objects()
        else:
            cursor = cls.objects(block_num=block_num)

        return cursor.order_by(order).first()

    @classmethod
    def avg_pow_fee(cls, block_num=None):
        if block_num is None:
            block_num = cls.get_latest_block_num()
        return cls.objects(block_num=block_num).average("pow_fee")

    @classmethod
    def calc_pow_window(cls, block_num=None):
        last_pow_work = cls.get_latest_work(block_num=block_num)
        if not last_pow_work:
            return None, None

        block_num = last_pow_work.block_num

        first_pow_work = cls.get_latest_work(block_num=block_num, order="start_time")

        return first_pow_work.start_time, last_pow_work.expire_time

    @classmethod
    def epoch_difficulty(cls, block_num=None):
        if block_num is None:
            block_num = cls.get_latest_block_num()

        return [
            ethash.boundary_to_hashpower(boundary)
            for boundary in cls.query(block_num=block_num).distinct("boundary")
        ]

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
                               finished_time=datetime.utcnow(), pow_fee=self.pow_fee,
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
    pow_fee = mg.FloatField(default=0.0)
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

    @classmethod
    def epoch_rewards(cls, block_num=None, miner_wallet=None, worker_name=None):
        match = {}
        if block_num is not None:
            if isinstance(block_num, int):
                match = {
                    "block_num": {
                        "$eq": block_num,
                    }
                }
            else:
                start, end = block_num
                match = {
                    "block_num": {
                        "$gte": start,
                        "$lte": end,
                    }
                }

        if miner_wallet is not None:
            match.update({
                "miner_wallet": {
                    "$eq": miner_wallet,
                }
            })

        if worker_name is not None:
            match.update({
                "worker_name": {
                    "$eq": worker_name,
                }
            })

        group = {
            "_id": None,
            "rewards": {"$sum": "$pow_fee"},
            "count": {"$sum": 1},
            "first_work_at": {"$min": "$finished_time"},
            "last_work_at": {"$max": "$finished_time"}
        }

        pipeline = [
            {"$match": match},
            {"$group": group},
        ]

        res = list(cls.objects.aggregate(*pipeline))
        if res:
            rewards = res[0]
            rewards.pop("_id", None)
            return rewards

        return {"rewards": None, "count": None,
                "first_work_at": None, "last_work_at": None}

    def get_worker(self):
        return miner.Worker.get_or_create(self.miner_wallet, self.worker_name)
