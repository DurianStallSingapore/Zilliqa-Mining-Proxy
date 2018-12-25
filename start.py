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
    conf_file = os.path.join(cur_dir, "pool.conf")
    poolserver.start_api_server(conf_file=conf_file, port=port)


if __name__ == "__main__":
    _port = None
    if len(sys.argv) > 1:
        _port = int(sys.argv[1])
    main(_port)
