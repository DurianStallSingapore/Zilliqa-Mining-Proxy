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

import os

from zilpool.common.utils import merge_config

cur_dir = os.path.dirname(os.path.abspath(__file__))


def get_config(conf):
    conf_file = os.path.join(cur_dir, conf)
    return merge_config(conf_file)


def get_database_debug_config():
    return get_config("database/debug.conf")


def get_pool_config():
    return get_config("../../../pool.conf")


def get_default_config():
    return get_config("../default.conf")
