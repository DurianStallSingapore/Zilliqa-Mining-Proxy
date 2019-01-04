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


def start_api_server(conf_file=None, port=None):
    from zilpool.common import utils
    from zilpool.apis import load_apis
    from zilpool.database import init_db

    # merge user's config with default.conf
    config = utils.merge_config(conf_file)

    # setup logfile
    setup_logging(config.logging)

    # init database and apis
    init_db(config)
    load_apis(config)

    # init app
    if port is None:
        port = config.api_server.get("port", "4202")
    api_path = config.api_server.get("path", "/api")
    host = config.api_server.get("host", "0.0.0.0")

    app = web.Application(debug=config.debug)
    app.router.add_post(api_path, create_api_handler(config))

    # start ioloop
    logging.critical(f"API endpoint: http://{host}:{port}{api_path}")
    web.run_app(app, host=host, port=port)
