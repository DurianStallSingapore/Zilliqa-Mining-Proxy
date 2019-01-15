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
"""
  Database
"""

import logging
from functools import wraps
from inspect import isclass

from mongoengine import connect, Document, OperationError
from mongoengine.connection import get_db, MongoEngineConnectionError

from zilpool.common.local import LocalProxy

db = LocalProxy(get_db)


def connect_to_db(config=None):
    """ connect_to_db at the begin of app initializing
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
    def count(cls, q_obj=None, **query):
        return cls.objects(q_obj=q_obj, **query).count()

    @classmethod
    def aggregate_count(cls, match, group):
        pipeline = [
            {"$match": match},
            {"$group": group},
            {"$count": "count"},
        ]

        res = list(cls.objects.aggregate(*pipeline))
        return res[0]["count"] if res else 0

    @classmethod
    @fail_safe
    def get(cls, first=True, order=None, **kwargs):
        cursor = cls.objects(**kwargs)
        if order is not None:
            cursor = cursor.order_by(order)
        if first:
            return cursor.first()
        else:
            return cursor.all()

    @classmethod
    def get_all(cls, order=None, **kwargs):
        return cls.get(first=False, order=order, **kwargs)

    @classmethod
    def get_one(cls, order=None, **kwargs):
        return cls.get(first=True, order=order, **kwargs)

    @classmethod
    def exist(cls, **kwargs):
        return cls.objects(**kwargs).first()

    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs)

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
    from . import ziladmin

    db_models = []
    for module in [miner, pow, zilnode, ziladmin]:
        for name in dir(module):
            obj = getattr(module, name)
            if isclass(obj) and issubclass(obj, Document):
                db_models.append(obj)

    return list(set(db_models))


def init_db(config):
    init_admin(config)


def init_admin(config):
    from . import ziladmin
    from zilpool.pyzil import crypto
    from zilpool.common.mail import EmailClient

    EmailClient.set_config(config)

    admin_emails = config["pool"]["admins"]

    for email in admin_emails:
        admin = ziladmin.ZilAdmin.get_one(email=email)

        if not admin:
            logging.critical("init admin database")
            password = crypto.rand_string(8)
            print(f"generate admin password: {password}")
            admin = ziladmin.ZilAdmin.create(email, password)
            if not admin:
                raise RuntimeError("Failed to create admin database")

            EmailClient.send_admin_mail(
                email,
                subject="password generated",
                msg=f"admin email: {email}\npassword: {password}"
            )
