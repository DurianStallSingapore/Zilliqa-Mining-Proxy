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


class ZilNodeOwner(ModelMixin, mg.Document):
    meta = {"collection": "zil_nodes_owner"}

    email = mg.StringField(max_length=128, required=True, unique=True)
    password_hash = mg.StringField(max_length=128)
    email_verified = mg.BooleanField(default=False)
    join_date = mg.DateTimeField()

    pow_fee = mg.FloatField(default=0.0)
    balance = mg.FloatField(default=0.0)

    pending_nodes = mg.ListField()

    @classmethod
    def create(cls, email):
        return cls(email=email, email_verified=False,
                   pow_fee=0.0, balance=0.0,
                   join_date=datetime.utcnow(),
                   pending_nodes=[]).save()

    def register_node(self, pub_key):
        node = ZilNode.get_by_pub_key(pub_key, authorized=None)
        if not node:
            node = ZilNode(pub_key=pub_key, authorized=False,
                           email=self.email, pow_fee=self.pow_fee)
            node.save()
        if node and node.authorized:
            return node

        if pub_key not in self.pending_nodes:
            self.pending_nodes.append(pub_key)
            self.save()

        return node

    def node_approved(self, pub_key):
        if pub_key in self.pending_nodes:
            self.pending_nodes.remove(pub_key)
        self.save()
        return self.pending_nodes


class ZilNode(ModelMixin, mg.Document):
    meta = {"collection": "zil_nodes"}

    pub_key = mg.StringField(max_length=128, required=True, unique=True)
    pow_fee = mg.FloatField(default=0.0)
    authorized = mg.BooleanField(default=False)
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
                "$gte": one_day,
            }
        }
        group = {
            "_id": {"pub_key": "$pub_key"},
        }

        return pow.PowWork.aggregate_count(match, group)
