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

import os
import yaml
import collections


cur_dir = os.path.dirname(os.path.abspath(__file__))


def app_path(*args) -> str:
    return os.path.join(cur_dir, *args)


class MagicDict(dict):
    """ A dict with magic, you can access dict value like attributes. """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


def load_config(conf=app_path("default.conf")) -> MagicDict:
    """ Load configs from yaml file.
    :param conf: config filename
    :return: dict
    """
    with open(conf, "rb") as f:
        return MagicDict(yaml.load(f))


def merge_config(new_conf=None) -> MagicDict:
    """ Merge new configs with default.conf """
    config = load_config(app_path("default.conf"))
    if new_conf:
        new_config = load_config(new_conf)
        dict_merge(config, new_config)
    return MagicDict(config)


def dict_merge(dct, merge_dct) -> None:
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurse down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed, change inplace
    :param merge_dct: new dct merged into dct
    :return: None
    """
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]
