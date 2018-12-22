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

from mongoengine import connect, Document, OperationError
from mongoengine.connection import get_db

from ..common.local import LocalProxy

db = LocalProxy(get_db)


def init_db(config=None):
    """ init_db at the begin of app initializing
    :param config: loaded config dict
    :return: None
    """
    uri = config.database["uri"]

    logging.info(f"Connecting to {uri}")
    connect(host=uri)
    logging.info("Database connected!")


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
    from .miner import Miner
    from .pow import PowWork, PowResult
    from .zilnode import ZilNode

    return Miner, PowWork, PowResult, ZilNode
