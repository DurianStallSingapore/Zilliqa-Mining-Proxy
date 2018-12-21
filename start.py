# -*- coding: utf-8 -*-
"""
zilpool start file

Copyright 2018, Gully Chen.
Licensed under Apache License, Version 2.0.
"""

import os
from zilpool import poolserver

cur_dir = os.path.dirname(os.path.abspath(__file__))
conf_file = os.path.join(cur_dir, "pool.conf")

poolserver.start(conf_file=conf_file)
