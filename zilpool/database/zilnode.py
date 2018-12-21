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

from .basemodel import db, db_required, MongoDocument


class ZilNode(MongoDocument):
    _collection = "zil_nodes"
    _indexes = [
        ("pub_key", {"unique": True}),
    ]
    _fields = ("pub_key", "pow_fee", "authorized")

    def __init__(self, pub_key: str, pow_fee: float=0.0, authorized: bool=False,
                 **kwargs):
        super().__init__(pub_key=pub_key, pow_fee=pow_fee, authorized=authorized,
                         **kwargs)

    def save_to_db(self):
        if not self.exist(self.pub_key):
            res = self.collection.insert_one(self.doc)
            return res.acknowledged
        return False

    @classmethod
    def exist(cls, pub_key):
        return cls.get_by_pub_key(pub_key=pub_key) is not None

    @classmethod
    def get_by_pub_key(cls, pub_key, authorized=None):
        if authorized is None:
            res = cls.find_one(pub_key=pub_key)
        else:
            res = cls.find_one(pub_key=pub_key, authorized=authorized)
        return res
