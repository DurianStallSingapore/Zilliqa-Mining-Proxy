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
    authorized = mg.BooleanField(default=True)

    nick_name = mg.StringField(max_length=64, default="")
    email = mg.StringField(max_length=128)
    join_date = mg.DateTimeField(default=datetime.utcnow)
    last_updated = mg.DateTimeField(default=datetime.utcnow)


class Worker(ModelMixin, mg.Document):
    meta = {"collection": "zil_mine_workers"}

    wallet_address = mg.StringField(max_length=128, required=True)
    worker_name = mg.StringField(max_length=64, default="")

    work_submitted = mg.IntField(default=0)
    work_failed = mg.IntField(default=0)
    work_finished = mg.IntField(default=0)
    work_verified = mg.IntField(default=0)


class HashRate(ModelMixin, mg.Document):
    meta = {"collection": "zil_mine_hashrate"}

    wallet_address = mg.StringField(max_length=128, required=True)
    worker_name = mg.StringField(max_length=64, default="")

    hashrate = mg.FloatField(default=0.0, required=True)
    updated_time = mg.DateTimeField(default=datetime.utcnow)
