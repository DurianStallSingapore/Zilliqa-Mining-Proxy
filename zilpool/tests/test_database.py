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

import pytest

from zilpool.database import init_db
from zilpool.tests import config


class TestDatabase:
    init_db(config)

    def test_init(self):
        pass

    def test_zil_nodes(self):
        from zilpool.database.zilnode import ZilNode

    def test_pow_work(self):
        from zilpool.database.pow import PowWork, PowResult
