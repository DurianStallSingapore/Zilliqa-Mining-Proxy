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

import asyncio
from json import dumps
from functools import partial
from aiohttp import web
from jsonrpcserver import async_dispatch
from jsonrpcserver.response import ExceptionResponse


# setup root logger
FORMATTER = logging.Formatter(
    "[%(asctime)s %(levelname)-6s %(filename)s:%(lineno)s] %(message)s"
)

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.INFO)

std_handler = logging.StreamHandler()
std_handler.setFormatter(FORMATTER)
rootLogger.addHandler(std_handler)


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
        request = await request.text()
        response = await async_dispatch(request,
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


def start_servers(conf_file=None, host=None, port=None):
    from zilpool.common import utils, mail
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

    # init app
    app = web.Application(debug=config["debug"])
    init_apis(app, config)
    init_website(app, config)

    # start the server
    if port is None:
        port = config["api_server"].get("port", "4202")
    if host is None:
        host = config["api_server"].get("host", "0.0.0.0")

    runner = web.AppRunner(app)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, host=host, port=port)
    loop.run_until_complete(site.start())

    # update config
    update_config(site, config)

    # start ioloop
    loop.run_forever()
