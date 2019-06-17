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
pool servers
"""

import logging
from logging import handlers

import time

import asyncio
from json import dumps
from functools import partial
from aiohttp import web
from jsonrpcserver import async_dispatch
from jsonrpcserver.response import ExceptionResponse

from zilpool import backgound
from zilpool.stratum.stratum_server import *

from zilpool.common import utils, blockchain
from zilpool.pyzil import crypto
from zilpool.nicehash import NiceHashClient

# setup root logger
FORMATTER = logging.Formatter(
    "[%(asctime)s %(levelname)-6s %(filename)s:%(lineno)s] %(message)s"
)

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.INFO)

std_handler = logging.StreamHandler()
std_handler.setFormatter(FORMATTER)
rootLogger.addHandler(std_handler)

isNinceHashOrderPlaced=False

def setup_logging(log_config):
    level = log_config.get("level", "info").upper()
    logging.getLogger().setLevel(level=level)
    logfile = log_config.get("file", "")
    if logfile:
        backup_count = log_config.get("backup_count", 5)
        rotating_size = log_config.get("rotating_size", 8)
        fh = handlers.RotatingFileHandler(
            logfile, maxBytes=rotating_size * 1024 * 1024, backupCount=backup_count
        )
        fh.setFormatter(FORMATTER)
        rootLogger.addHandler(fh)


def create_api_handler(config=None):
    compat_dumps = partial(dumps, separators=(",", ":"))

    async def api_handle(request: web.Request) -> web.Response:
        request_text = await request.text()
        response = await async_dispatch(request_text,
                                        context=request,
                                        debug=config.debug,
                                        basic_logging=False,
                                        trim_log_values=True)

        if isinstance(response, ExceptionResponse):
            logging.error("Server Error", exc_info=response.exc)
        if response.wanted:
            return web.json_response(response.deserialized(),
                                     status=response.http_status,
                                     dumps=compat_dumps)
        else:
            return web.Response()
    return api_handle


def init_apis(app, config):
    from zilpool.apis import load_apis

    load_apis(config)

    if not config["api_server"].get("enabled"):
        return

    path = config["api_server"].get("path", "/api")

    app.router.add_post(path, create_api_handler(config))


def init_website(app, config):
    from zilpool.web import init_web_handlers

    if not config["api_server"]["website"].get("enabled"):
        return

    init_web_handlers(app, config)


def update_config(site, config):
    if config["api_server"].get("enabled"):
        api_path = config["api_server"]["path"]
        api_url = f"{site.name}{api_path}"
        logging.critical(f"API Server running at: {api_url}")

        if not config["api_server"]["url"]:
            # set auto generated api url
            config["api_server"]["url"] = api_url

    website_config = config["api_server"]["website"]
    if website_config.get("enabled"):
        web_path = website_config["path"]
        web_url = f"{site.name}{web_path}"
        logging.critical(f"Website running at: {web_url}")

        if not website_config["url"]:
            # set auto generated website url
            website_config["url"] = web_url

def add_stratum_protocol(config):
    proto = lambda: StratumServerProtocol(config)
    return proto

async def start_stratum(config):
    # run stratum server
    port = config["stratum_server"].get("port", "33456")
    host = config["stratum_server"].get("host", "0.0.0.0")

    loop = asyncio.get_running_loop()
    server = await loop.create_server(add_stratum_protocol(config), host, port)

    logging.info(f"Stratum server running at: {host}:{port}")

    async with server:
        await server.serve_forever()

def schedule_coroutine(target, *, loop=None):
    """Schedules target coroutine in the given event loop

    If not given, *loop* defaults to the current thread's event loop

    Returns the scheduled task.
    """
    if asyncio.iscoroutine(target):
        return asyncio.ensure_future(target, loop=loop)
    raise TypeError("target must be a coroutine, "
                    "not {!r}".format(type(target)))

async def create_dummy_work():
    DUMMY_WORK_INTERVAL = 15
    while True:
        logging.info("Run to create dummy work")

        if len(stratumMiners) <= 0:
            await asyncio.sleep(DUMMY_WORK_INTERVAL)
            continue

        txBlock = await blockchain.Zilliqa.get_current_txblock()
        txBlockMod = txBlock % 100
        if txBlockMod == 99 or txBlockMod == 0:
            logging.info(f"Block number {txBlock}, don't send dummy work")
            await asyncio.sleep(DUMMY_WORK_INTERVAL)
            continue

        header = crypto.bytes_to_hex_str(crypto.rand_bytes(32))
        dsBlockNum = await blockchain.Zilliqa.get_current_dsblock()
        difficulty = await blockchain.Zilliqa.get_difficulty()
        boundary = crypto.bytes_to_hex_str(ethash.difficulty_to_boundary_divided(difficulty))
        pubKeyStr = "03FB81D476B3CF161AFD1AE0B861ECC907111AB891DF82028DD3D3085E2460A574"
        privKeyStr = "224B31816F0B529F21B14D9F04C42E7F277A024758A57BB6E1B3DEBF39A38E72"
        signature = "C6B47C86A42F5F0B62DD2E6485733EF1D96EA82DD8D200EF46BD4100D133E16293B0089AE77AF6C3AF048F0D65911A254722B42CDF4C3514CE11F33FD78B2A65"
        work = pow.PowWork.new_work(header, dsBlockNum, boundary,
                                    pub_key=pubKeyStr, signature=signature,
                                    timeout=60, pow_fee=0)

        for stratumMiner in stratumMiners:
            stratumMiner.notify_work(work, False)

        await asyncio.sleep(DUMMY_WORK_INTERVAL)

async def nice_hash_task(config):
    client = NiceHashClient(config.nicehash)
    global isNinceHashOrderPlaced

    while True:
        txBlock = await blockchain.Zilliqa.get_current_txblock()
        logging.info(f"Current block number {txBlock}")
        txBlockMod = txBlock % 100
        blockToPlaceOrder = config.nicehash.get("place_order_block", 97)
        if txBlockMod == blockToPlaceOrder and isNinceHashOrderPlaced is not True:
            logging.info(f"Start place order in nicehash")
            # create order
            order_number = await client.create_order(amount=0.02, price=2.00, limit=1)
            logging.info(f"Order number {order_number}")
            isNinceHashOrderPlaced = True
        elif isNinceHashOrderPlaced and txBlockMod >= blockToPlaceOrder:
            logging.info(f"Keep my order on top")
            await client.keep_my_orders_top()
        elif txBlockMod == 1 and isNinceHashOrderPlaced:
            logging.info(f"Stop all of my orders")
            await client.stop_all()
            isNinceHashOrderPlaced = False


        await asyncio.sleep(10)


async def start_servers(conf_file=None, host=None, port=None):
    from zilpool.common import utils, mail, blockchain
    from zilpool.database import init_db, connect_to_db

    # merge user's config with default.conf
    config = utils.merge_config(conf_file)

    # setup logfile
    setup_logging(config["logging"])

    # init tools
    mail.EmailClient.set_config(config)

    # init database
    connect_to_db(config)
    init_db(config)

    # init Zilliqa network APIs
    blockchain.Zilliqa.init(config)

    # init app
    app = web.Application(debug=config["debug"])
    init_apis(app, config)
    init_website(app, config)

    # start background tasks
    app["config"] = config
    app.on_startup.append(backgound.start_background_tasks)
    app.on_cleanup.append(backgound.cleanup_background_tasks)

    # start the server
    if port is None:
        port = config["api_server"].get("port", "4202")
    if host is None:
        host = config["api_server"].get("host", "0.0.0.0")

    runner = web.AppRunner(app)
    loop = asyncio.get_event_loop()

    await runner.setup()
    #loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, host=host, port=port)
    #loop.run_until_complete(site.start())
    await(site.start())

    # update config
    update_config(site, config)

    schedule_coroutine(nice_hash_task(config), loop=loop)
    schedule_coroutine(create_dummy_work(), loop=loop)

    # start stratum server
    await start_stratum(config)
