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


import logging
from datetime import datetime, timedelta

import mongoengine as mg
from mongoengine import Q

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

    def works_stats(self):
        from .pow import PowWork, PowResult

        working_q = Q(expire_time__gte=datetime.utcnow()) & Q(finished=False)

        return {
            "all": PowWork.count(pub_key=self.pub_key),
            "working": PowWork.count(working_q, pub_key=self.pub_key),
            "finished": PowWork.count(pub_key=self.pub_key, finished=True),
            "verified": PowResult.count(pub_key=self.pub_key, verified=True),
        }
