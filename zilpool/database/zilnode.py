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

import mongoengine as db

from .basemodel import ModelMixin


class ZilNode(ModelMixin, db.Document):
    meta = {"collection": "zil_nodes"}

    pub_key = db.StringField(max_length=128, required=True, unique=True)
    pow_fee = db.FloatField(default=0.0)
    authorized = db.BooleanField(default=False)

    @classmethod
    def get_by_pub_key(cls, pub_key, authorized=True):
        query = db.Q(pub_key=pub_key)
        if authorized is not None:
            query = query & db.Q(authorized=authorized)
        return cls.objects(query).first()
