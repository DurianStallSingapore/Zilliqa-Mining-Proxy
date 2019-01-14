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
"""
start file
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
