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
backgound tasks
"""
import time
import logging

import asyncio
from zilpool.common import utils
from zilpool.pyzil.zilliqa_api import APIError


async def update_chain_info(config):
    try:
        prev_block = None
        prev_time = None
        latest_blocks_time = []
        while True:
            try:
                cur_block = utils.Zilliqa.get_current_txblock()
                if cur_block:
                    if prev_block is None:
                        prev_block = cur_block
                        prev_time = time.time()
                    else:
                        if cur_block < prev_block:
                            utils.Zilliqa.clear_cache()
                            continue

                        if cur_block > prev_block:
                            blocks = cur_block - prev_block
                            now = time.time()

                            elapsed = now - prev_time
                            block_time = elapsed / blocks
                            latest_blocks_time.append(block_time)

                            avg_time = sum(latest_blocks_time) / len(latest_blocks_time)
                            utils.Zilliqa.update_avg_block_time(avg_time)

                            prev_block = cur_block
                            prev_time = now

                            if len(latest_blocks_time) > 50:
                                latest_blocks_time = latest_blocks_time[25:]

            except APIError as e:
                logging.error(f"APIError {e}")

            await asyncio.sleep(config["zilliqa"]["update_interval"])
    except asyncio.CancelledError:
        pass
    except:
        logging.exception("unknown error in update_chain_info")
        raise
    finally:
        pass


async def start_background_tasks(app):
    config = app["config"]
    if config["zilliqa"]["enabled"]:
        app["zil_background"] = app.loop.create_task(update_chain_info(config))


async def cleanup_background_tasks(app):
    if "zil_background" in app:
        app["zil_background"].cancel()
        await app["zil_background"]
