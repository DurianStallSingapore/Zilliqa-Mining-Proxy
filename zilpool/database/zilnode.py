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

from .basemodel import ModelMixin


class ZilNode(ModelMixin, mg.Document):
    meta = {"collection": "zil_nodes"}

    pub_key = mg.StringField(max_length=128, required=True, unique=True)
    pow_fee = mg.FloatField(default=0.0)
    authorized = mg.BooleanField(default=False)
    balance = mg.FloatField(default=0.0)
    email = mg.StringField(max_length=128)

    def __str__(self):
        return f"[ZilNode: {self.pub_key}, {self.authorized}]"

    @classmethod
    def get_by_pub_key(cls, pub_key, authorized=True):
        query = mg.Q(pub_key=pub_key)
        if authorized is not None:
            query = query & mg.Q(authorized=authorized)
        return cls.objects(query).first()

    @classmethod
    def active_count(cls):
        from . import pow
        one_day = datetime.utcnow() - timedelta(days=1)

        match = {
            "start_time": {
                '$gte': one_day,
            }
        }
        group = {
            "_id": {"pub_key": "$pub_key"},
        }

        return pow.PowWork.aggregate_count(match, group)
