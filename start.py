# -*- coding: utf-8 -*-
"""
zilpool start file

Copyright 2018, Gully Chen.
Licensed under Apache License, Version 2.0.
"""

import os
import sys
from zilpool import poolserver

cur_dir = os.path.dirname(os.path.abspath(__file__))


def main(port=None):
    if port is not None:
        port = int(port)
    conf_file = os.path.join(cur_dir, "pool.conf")
    poolserver.start_servers(conf_file=conf_file,
                             port=port)


if __name__ == "__main__":
    main(*sys.argv[1:2])
