# -*- coding: utf-8 -*-

from . import zil
from . import eth
from . import stats
from . import users
from . import admin


def load_apis(config=None):
    zil.init_apis(config)

    eth.init_apis(config)

    stats.init_apis(config)

    users.init_apis(config)

    admin.init_apis(config)
