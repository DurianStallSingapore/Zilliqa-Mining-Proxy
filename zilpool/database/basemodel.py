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

import abc
import logging
from functools import wraps
from collections import OrderedDict

from ..common.utils import MagicDict
from ..common.local import LocalProxy

from pymongo import MongoClient
from pymongo.operations import IndexModel


class DataBaseError(Exception):
    pass

# global db instance
_global_db = None

# global db proxy
db = LocalProxy(lambda: _global_db)


def init_db(config=None):
    """ init_db at the begin of app initializing
    :param config: loaded config dict
    :return: db instance
    """
    global _global_db
    uri = config.database["uri"]
    logging.info(f"Connecting to {uri}")

    try:
        client = MongoClient(uri)
        logging.info(f"Connected to server version {client.server_info()['version']}")

        # get database
        _global_db = client.get_database()
        _global_db.command("ping")
        _global_db.connected = True
    except:
        logging.fatal(f"Failed to init database {uri}")
        raise DataBaseError("Init failed")

    create_indexes()

    return _global_db


def db_required(f):
    @wraps(f)
    def check_db_and_call(*args, **kwds):
        global _global_db
        if _global_db is None:
            logging.fatal("database not inited")
            raise DataBaseError("database not inited")
        if not _global_db.connected:
            logging.fatal("database not connected")
            raise DataBaseError("database not connected")
        return f(*args, **kwds)
    return check_db_and_call


@db_required
def create_indexes():
    from .miner import Miner
    from .pow import PowWork, PowResult
    from .zilnode import ZilNode

    for cls in (Miner, PowWork, PowResult, ZilNode):
        cls.create_indexes()


@db_required
def drop_collection(*args, **kwargs):
    return db.drop_collection(*args, **kwargs)


class MongoDocument(abc.ABC):
    _collection = ""
    _indexes = ()
    _fields = ()

    def __init__(self, **kwargs):
        self._dict = MagicDict(**kwargs)

    def __repr__(self):
        return f"[{self.__class__.__name__}: {self.doc}]"

    def __getattr__(self, item):
        return self._dict[item]

    def __getitem__(self, item):
        return self._dict[item]

    def __setitem__(self, key, value):
        self._dict[key] = value

    @property
    def values(self):
        # must corresponding to self._fields
        def get_attr(field):
            if hasattr(self, field):
                return getattr(self, field)
            if isinstance(self, dict):
                return self[field]
            raise AttributeError(f"'{type(self)}' object has no attribute '{field}'")

        return tuple(map(get_attr, self._fields))

    @property
    def fields(self):
        return self._fields

    @property
    def doc(self):
        t = self.values
        assert len(t) == len(self._fields)
        return OrderedDict(zip(self._fields, t))

    @property
    def dict(self):
        return self._dict

    @property
    def collection(self):
        assert len(self._collection) > 0
        return db[self._collection]

    @classmethod
    def db_collection(cls):
        assert len(cls._collection) > 0
        return db[cls._collection]

    @classmethod
    def create_indexes(cls):
        if not cls._indexes:
            return
        indexes = []
        for index in cls._indexes:
            keys, kwargs = index
            idx_model = IndexModel(keys, **kwargs)
            indexes.append(idx_model)
        return cls.db_collection().create_indexes(indexes)

    @classmethod
    def find_one(cls, id_or_filter=None, *args, **kwargs):
        if id_or_filter is None:
            id_or_filter = kwargs
            kwargs = {}
        res = cls.db_collection().find_one(id_or_filter, *args, **kwargs)
        if res is None:
            return None
        return cls(**res)


