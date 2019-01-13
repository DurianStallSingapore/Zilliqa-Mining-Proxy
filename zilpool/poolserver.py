# -*- coding: utf-8 -*-
# Zilliqa Mining Pool
# Copyright  @ 2018-2019 Gully Chen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        fh = handlers.RotatingFileHandler(
            logfile, maxBytes=8 * 1024 * 1024, backupCount=5
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

        config["api_server"]["url"] = api_url
        config["pool"]["api_endpoints"].append(api_url)
        logging.critical(f"API Server running at: {api_url}")

    website_config = config["api_server"]["website"]
    if website_config.get("enabled"):
        web_path = website_config["path"]
        web_url = f"{site.name}{web_path}"
        website_config["url"] = web_url
        logging.critical(f"Website running at: {web_url}")


def start_servers(conf_file=None, port=None):
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
