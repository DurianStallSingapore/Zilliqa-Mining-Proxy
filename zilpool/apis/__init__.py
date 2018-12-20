# -*- coding: utf-8 -*-

from . import zil
from . import eth


def load_apis(config=None):
    if config.api_server["zil"]["enabled"]:
        zil.init_apis(config)

    if config.api_server["eth"]["enabled"]:
        eth.init_apis(config)
