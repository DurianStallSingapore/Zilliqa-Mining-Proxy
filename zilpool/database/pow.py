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
from typing import Optional
from datetime import datetime

import pymongo as mg

from .basemodel import db_required, MongoDocument


class PowWork(MongoDocument):
    _collection = "zil_pow_works"
    _indexes = [
        # datetime index
        ([("start_time", mg.DESCENDING)],
         {"name": "start time"}),
        # header_seed_boundary text index
        ([("header", mg.TEXT), ("seed", mg.TEXT), ("boundary", mg.TEXT)],
         {"name": "header_seed_boundary"}),
    ]
    _fields = ("header", "seed", "boundary", "pub_key",
               "start_time", "timeout", "finished",
               "miner", "pow_fee")

    def __init__(self, header: str, seed: str, boundary: str,
                 pub_key: Optional[str]=None,
                 signature: Optional[str]=None,
                 start_time=None, timeout=120, finished=0,
                 miner="", pow_fee=0.0, **kwargs):
        """ Create a PoW Work.
        :param header: the header hash
        :param seed:
        :param boundary:
        :param pub_key:
        :param signature:
        :param start_time:
        :param timeout: work timeout in seconds
        :param finished: finished time in seconds, 0 means not finished
        :param miner: the miner's zil wallet address who done the work
        :param pow_fee: get new works sort by fee
        """
        super().__init__(
            header=header, seed=seed, boundary=boundary,
            pub_key=pub_key, signature=signature,
            start_time=start_time or datetime.now(), timeout=timeout,
            finished=finished, pow_fee=pow_fee, miner=miner,
            **kwargs
        )

    def verify_signature(self)->bool:
        return True

    @db_required
    def save_to_db(self):
        logging.info(f"insert work {self}")
        res = self.collection.insert_one(self.doc)
        logging.info(f"work saved {res.inserted_id}")
        return res.acknowledged

    # class methods
    @classmethod
    @db_required
    def get_new_works(cls, count=1, min_fee=0.0):
        pass


class PowResult(MongoDocument):
    _collection = "zil_pow_results"
