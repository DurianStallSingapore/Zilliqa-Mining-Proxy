# -*- coding: utf-8 -*-

from . import zil
from . import eth
from . import stats


def load_apis(config=None):
    if config.api_server["zil"]["enabled"]:
        zil.init_apis(config)

    if config.api_server["eth"]["enabled"]:
        eth.init_apis(config)

    if config.api_server["stats"]["enabled"]:
        stats.init_apis(config)
