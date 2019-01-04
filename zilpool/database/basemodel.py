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
from functools import wraps
from inspect import isclass

from mongoengine import connect, Document, OperationError
from mongoengine.connection import get_db, MongoEngineConnectionError

from zilpool.common.local import LocalProxy

db = LocalProxy(get_db)


def init_db(config=None):
    """ init_db at the begin of app initializing
    :param config: loaded config dict
    :return: None
    """
    uri = config.database["uri"]

    logging.critical(f"Connecting to {uri}")
    try:
        connect(host=uri)
        logging.critical("Database connected!")
    except MongoEngineConnectionError:
        logging.fatal("Failed connect to MongoDB!")
        raise


def fail_safe(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except OperationError:
            logging.warning(f"MongoDB OperationError in {f.__name__}")
            return None
    return wrapper


def drop_all():
    db.client.drop_database(db.name)


class ModelMixin:

    @classmethod
    @fail_safe
    def get(cls, first=True, **kwargs):
        cursor = cls.objects(**kwargs)
        if first:
            return cursor.first()
        else:
            return cursor.all()

    @wraps(Document.save)
    @fail_safe
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.reload()
        return self

    @wraps(Document.update)
    @fail_safe
    def update(self, **kwargs):
        res = super().update(**kwargs)
        if not res:
            return None
        self.reload()
        return self


def get_all_models():
    from . import miner
    from . import pow
    from . import zilnode

    db_models = []
    for module in [miner, pow, zilnode]:
        for name in dir(module):
            obj = getattr(module, name)
            if isclass(obj) and issubclass(obj, Document):
                db_models.append(obj)

    return list(set(db_models))
