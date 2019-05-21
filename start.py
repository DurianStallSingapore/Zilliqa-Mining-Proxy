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
import argparse
import asyncio
from zilpool import poolserver
#from zilpool.stratum import stratum_server
from zilpool.stratum.stratum_server import StratumServerProtocol

cur_dir = os.path.dirname(os.path.abspath(__file__))

async def main():
    parser = argparse.ArgumentParser(
        description="Run Zilliqa Mining Proxy",
        usage="""python start.py --conf pool.conf --port 4202"""
    )
    parser.add_argument("-c", "--conf", help="conf file", default="")
    parser.add_argument("-host", "--host", help="host to listen", default="")
    parser.add_argument("-p", "--port", help="port to listen", type=int, default=0)
    args = parser.parse_args()

    if args.conf:
        conf_file = args.conf
    else:
        conf_file = os.path.join(cur_dir, "pool.conf")

    host = args.host if args.host else None
    port = args.port if args.port else None

    await poolserver.start_servers(conf_file=conf_file, host=host, port=port)


#if __name__ == "__main__":
asyncio.run(main())
